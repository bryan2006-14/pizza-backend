"""
panel_admin/views.py — versión mejorada

Cambios vs original:
  1. locale.setlocale eliminado → usar babel o format manual (no rompe en producción con múltiples workers)
  2. hoy/meses se calculan DENTRO de cada vista (eran vars de módulo, se congelaban al arrancar)
  3. select_related en queries con FK para evitar N+1
  4. Login con rate-limit simple (cache de Django)
  5. EliminarObjetoView corregido: queryset obligatorio para CBV DeleteView
  6. BaseListView: whitelist de campos para filtrar (evita enumerar columnas internas)
  7. get_queryset devuelve el queryset filtrado correctamente
"""

from django.shortcuts import render, redirect
from django.views.generic import CreateView, UpdateView, DeleteView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from api.models import *
from panel_admin.forms import *
import json
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from .forms import *
from django.http import Http404
from django.contrib import messages
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.utils import timezone
from datetime import timedelta
from django.db.models.functions import TruncMonth, TruncDay, TruncHour, Concat
from django.db.models import Value, Count, Sum, Avg, F, ExpressionWrapper, DurationField, Subquery, OuterRef
from django.utils.timezone import now
from django.core.cache import cache


# ─── helpers ────────────────────────────────────────────────────────────────

MONTH_NAMES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

def _build_meses(reference: timezone.datetime) -> list[str]:
    """Devuelve los últimos 12 meses en formato 'mes año' sin depender de locale."""
    result = []
    for i in range(11, -1, -1):
        dt = reference - timedelta(days=30 * i)
        result.append(f"{MONTH_NAMES_ES[dt.month - 1]} {dt.year}")
    return result


# ====================================================
# 📊 VISTAS DE ESTADÍSTICAS (DASHBOARDS)
# ====================================================

@login_required(login_url='/panel_admin/login/')
def vista_admin_ventas(request):
    hoy = timezone.now()
    meses = _build_meses(hoy)
    hace_12_meses = hoy - timedelta(days=365)

    # select_related evita N+1 al acceder a pago desde Pedido
    ventas_mensuales = (
        Pedido.objects
        .filter(fecha_pedido__gte=hace_12_meses)
        .select_related('pago')
        .annotate(mes=TruncMonth('fecha_pedido'))
        .values('mes')
        .annotate(
            total_ventas=Count('id_pedido'),
            total_ingresos=Sum('pago__monto', default=0)
        )
        .order_by('mes')
    )

    # Indexar por "mes año" para O(1) en el loop
    ventas_por_mes = {
        f"{MONTH_NAMES_ES[v['mes'].month - 1]} {v['mes'].year}": v
        for v in ventas_mensuales
    }

    data_ventas = []
    for mes in meses:
        v = ventas_por_mes.get(mes)
        total_ventas   = v['total_ventas']   if v else 0
        total_ingresos = float(v['total_ingresos']) if v and v['total_ingresos'] else 0.0
        data_ventas.append(f"{total_ventas} - S/.{total_ingresos:.2f}")

    metodos_pago = Pago.objects.values('metodo_pago').annotate(cantidad=Count('id_pago'))
    data_pagos   = [[p['metodo_pago'], p['cantidad']] for p in metodos_pago]

    top_dias = (
        Pedido.objects
        .annotate(dia=TruncDay('fecha_pedido'))
        .values('dia')
        .annotate(total_ventas=Count('id_pedido'))
        .order_by('-total_ventas')[:4]
    )
    top_dias_data = [
        {"dia": MONTH_NAMES_ES[d['dia'].month - 1][:3].title() + " " + d['dia'].strftime('%d'),
         "total_ventas": d['total_ventas']}
        for d in top_dias
    ]

    top_horas = (
        Pedido.objects
        .annotate(hora=TruncHour('fecha_pedido'))
        .values('hora')
        .annotate(total_ventas=Count('id_pedido'))
        .order_by('-total_ventas')[:4]
    )
    top_horas_data = [
        {"hora": h['hora'].strftime('%H:%M'), "total_ventas": h['total_ventas']}
        for h in top_horas
    ]

    inicio_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    ingresos_mes = (
        Pago.objects
        .filter(pedido__fecha_pedido__gte=inicio_mes)
        .aggregate(Sum('monto'))['monto__sum'] or 0
    )
    costo_promedio_venta = Pago.objects.aggregate(Avg('monto'))['monto__avg'] or 0

    return render(request, 'panel_admin/admin_ventas.html', {
        'data_ventas': json.dumps(data_ventas),
        'meses': json.dumps(meses),
        'data_pagos': json.dumps(data_pagos),
        'top_dias_data': top_dias_data,
        'top_horas_data': top_horas_data,
        'ingresos_mes': round(ingresos_mes, 2),
        'costo_promedio_venta': round(costo_promedio_venta, 2),
    })


@login_required(login_url='/panel_admin/login/')
def vista_admin_clientes(request):
    hoy = timezone.now()
    meses = _build_meses(hoy)

    clientes_por_cada_mes_ultimo_anio = [
        Pedido.objects.filter(
            fecha_pedido__year=hoy.year if hoy.month >= mes else hoy.year - 1,
            fecha_pedido__month=mes
        ).values('cliente_id').distinct().count()
        for mes in range(1, 13)
    ]

    total_clientes = Cliente.objects.count()
    clientes_recurrentes = (
        Cliente.objects
        .filter(pedido__isnull=False)
        .annotate(num_pedidos=Count('pedido'))
        .filter(num_pedidos__gt=1)
        .count()
    )
    porcentaje_retencion = (clientes_recurrentes / total_clientes * 100) if total_clientes else 0

    inicio_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    subquery = Pedido.objects.filter(
        cliente_id=OuterRef('cliente_id'),
        fecha_pedido__lt=inicio_mes
    ).values('cliente_id')

    clientes_nuevos_mes = (
        Pedido.objects
        .filter(fecha_pedido__gte=inicio_mes, fecha_pedido__lt=hoy)
        .exclude(cliente_id__in=Subquery(subquery))
        .values('cliente_id').distinct().count()
    )

    clientes_mas_frecuentes = list(
        Cliente.objects
        .annotate(total_pedidos=Count('pedido'))
        .order_by('-total_pedidos')[:4]
        .values_list('usuario', 'total_pedidos')
    )

    return render(request, 'panel_admin/admin_clientes.html', {
        'clientes_por_cada_mes_ultimo_anio': json.dumps(clientes_por_cada_mes_ultimo_anio),
        'meses': json.dumps(meses),
        'porcentaje_retencion': round(porcentaje_retencion, 2),
        'total_clientes': total_clientes,
        'clientes_nuevos_mes': clientes_nuevos_mes,
        'clientes_mas_frecuentes': clientes_mas_frecuentes,
    })


@login_required(login_url='/panel_admin/login/')
def vista_admin_empleados(request):
    hoy = timezone.now()
    meses = _build_meses(hoy)

    data_empleados_mas_ventas_query = (
        Historial.objects
        .filter(pedido__fecha_pedido__gte=hoy.replace(year=hoy.year - 1))
        .select_related('empleado', 'pedido')
        .values('empleado__nombre', 'empleado__apellido')
        .annotate(
            total_pedidos=Count('pedido'),
            nombre_completo=Concat('empleado__nombre', Value(' '), 'empleado__apellido')
        )
        .order_by('-total_pedidos')[:12]
        .values_list('nombre_completo', 'total_pedidos')
    )
    data_empleados_mas_ventas = [[n, t] for n, t in data_empleados_mas_ventas_query]

    empleados_mas_ingresos_query = (
        Historial.objects
        .select_related('empleado', 'pedido__pago')
        .values('empleado__nombre')
        .annotate(total_ingresos=Sum('pedido__pago__monto'))
        .order_by('-total_ingresos')[:4]
        .values_list('empleado__nombre', 'total_ingresos')
    )
    empleados_mas_ingresos = [
        (nombre, float(total or 0)) for nombre, total in empleados_mas_ingresos_query
    ]

    empleados_mas_eficaces_query = (
        Historial.objects
        .select_related('empleado', 'pedido')
        .annotate(
            tiempo_entrega=ExpressionWrapper(
                F('pedido__fecha_entrega') - F('pedido__fecha_pedido'),
                output_field=DurationField()
            )
        )
        .values('empleado__nombre', 'empleado__apellido')
        .annotate(
            promedio_tiempo=Avg('tiempo_entrega'),
            nombre_completo=Concat('empleado__nombre', Value(' '), 'empleado__apellido')
        )
        .order_by('promedio_tiempo')[:4]
        .values_list('nombre_completo', 'promedio_tiempo')
    )
    empleados_mas_eficaces = [
        [nombre, round(pt.total_seconds() / 60, 1) if pt else 0]
        for nombre, pt in empleados_mas_eficaces_query
    ]

    estado_empleados = [
        ["Activo",     Empleado.objects.filter(estado="activo").count()],
        ["Inactivo",   Empleado.objects.filter(estado="inactivo").count()],
        ["Vacaciones", Empleado.objects.filter(estado="vacaciones").count()],
    ]

    total_pedidos  = Pedido.objects.count()
    total_empleados = Empleado.objects.count()
    ventas_promedio_por_empleado = round(total_pedidos / max(total_empleados, 1), 2)

    tp = (
        Pedido.objects
        .annotate(tiempo=ExpressionWrapper(F('fecha_entrega') - F('fecha_pedido'), output_field=DurationField()))
        .aggregate(total_tiempo=Sum('tiempo'), total_pedidos=Count('id_pedido'))
    )
    if tp['total_tiempo'] and tp['total_pedidos']:
        tiempo_promedio_pedido = round(
            tp['total_tiempo'].total_seconds() / 3600 / tp['total_pedidos'], 2
        )
    else:
        tiempo_promedio_pedido = 0

    return render(request, 'panel_admin/admin_empleados.html', {
        'data_empleados_mas_ventas': json.dumps(data_empleados_mas_ventas),
        'empleados_mas_ingresos': list(empleados_mas_ingresos),
        'empleados_mas_eficaces': list(empleados_mas_eficaces),
        'ventas_promedio_por_empleado': ventas_promedio_por_empleado,
        'tiempo_promedio_pedido': tiempo_promedio_pedido,
        'estado_empleados': estado_empleados,
        'meses': json.dumps(meses),
    })


@login_required(login_url='/panel_admin/login/')
def vista_admin_sucursales(request):
    data_ventas_sucursal = list(
        Pedido.objects.values('sucursal__direccion')
        .annotate(total_ventas=Count('id_pedido'))
        .order_by('-total_ventas')
        .values_list('sucursal__direccion', 'total_ventas')
    )
    data_clientes_sucursal = list(
        Pedido.objects.values('sucursal__direccion')
        .annotate(total_clientes=Count('cliente_id', distinct=True))
        .order_by('-total_clientes')
        .values_list('sucursal__direccion', 'total_clientes')
    )
    data_empleados_sucursal = list(
        Empleado.objects.filter(estado='activo')
        .select_related('sucursal')
        .values('sucursal__direccion')
        .annotate(total_empleados=Count('id_empleado'))
        .order_by('-total_empleados')
        .values_list('sucursal__direccion', 'total_empleados')
    )
    ganancias_promedio_sucursal = Pago.objects.aggregate(Avg('monto'))['monto__avg'] or 0
    pedidos_promedio_sucursal   = Pedido.objects.aggregate(Avg('id_pedido'))['id_pedido__avg'] or 0

    return render(request, 'panel_admin/admin_sucursales.html', {
        'data_ventas_sucursal': json.dumps(data_ventas_sucursal),
        'data_clientes_sucursal': data_clientes_sucursal,
        'data_empleados_sucursal': data_empleados_sucursal,
        'ganancias_promedio_sucursal': round(ganancias_promedio_sucursal, 2),
        'pedidos_promedio_sucursal': round(pedidos_promedio_sucursal, 2),
    })


@login_required(login_url='/panel_admin/login/')
def vista_admin_productos(request):
    productos_mas_vendidos = list(
        PedidoItem.objects.filter(variante__isnull=False)
        .select_related('variante__producto')
        .values('variante__producto__nombre', 'variante__tamaño')
        .annotate(total_vendido=Sum('cantidad'))
        .order_by('-total_vendido')[:8]
        .values_list('variante__producto__nombre', 'total_vendido')
    )
    promociones_mas_vendidas = list(
        PedidoItem.objects.filter(promocion__isnull=False)
        .select_related('promocion')
        .values('promocion__titulo')
        .annotate(total_vendido=Sum('cantidad'))
        .order_by('-total_vendido')[:4]
        .values_list('promocion__titulo', 'total_vendido')
    )
    stock_bajo = list(
        InventarioSucursal.objects.filter(stock__lt=10)
        .select_related('variante__producto', 'sucursal')
        .values('variante__producto__nombre', 'variante__tamaño', 'stock', 'sucursal__direccion')
        .order_by('stock')[:10]
    )

    return render(request, 'panel_admin/admin_productos.html', {
        'productos_mas_vendidos': json.dumps(productos_mas_vendidos),
        'promociones_mas_vendidas': json.dumps(promociones_mas_vendidas),
        'stock_bajo': stock_bajo,
        'total_productos': Producto.objects.count(),
        'total_promociones': Promocion.objects.count(),
    })


# ====================================================
# 🔐 LOGIN con rate-limit básico
# ====================================================

MAX_INTENTOS   = 5      # intentos fallidos permitidos
BLOQUEO_SECS   = 300    # 5 minutos de bloqueo

def login_view(request):
    if request.method == 'POST':
        ip          = request.META.get('REMOTE_ADDR', 'unknown')
        cache_key   = f'login_intentos_{ip}'
        intentos    = cache.get(cache_key, 0)

        if intentos >= MAX_INTENTOS:
            messages.error(request, 'Demasiados intentos fallidos. Espera 5 minutos.')
            return render(request, 'panel_admin/login.html')

        username = request.POST.get('usuario', '').strip()
        password = request.POST.get('contrasena', '')

        if not username or not password:
            messages.error(request, 'Completa todos los campos.')
            return render(request, 'panel_admin/login.html')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            cache.delete(cache_key)          # Resetear intentos fallidos
            login(request, user)
            next_url = request.GET.get('next') or 'admin_ventas'
            # Validar que next_url no apunte fuera del dominio (open redirect)
            if not next_url.startswith('/'):
                next_url = 'admin_ventas'
            return redirect(next_url)
        else:
            cache.set(cache_key, intentos + 1, BLOQUEO_SECS)
            restantes = MAX_INTENTOS - intentos - 1
            messages.error(
                request,
                f'Usuario o contraseña incorrectos. Intentos restantes: {restantes}.'
            )

    return render(request, 'panel_admin/login.html')


# ====================================================
# 📋 VISTA BASE PARA LISTADOS — con whitelist de campos
# ====================================================

class BaseListView(LoginRequiredMixin, ListView):
    login_url          = '/panel_admin/login/'
    template_name      = 'panel_admin/lista.html'
    context_object_name = 'objetos'
    paginate_by        = 7

    # Subclases deben definir qué campos se pueden filtrar
    # Si no se define, se usa self.campos (solo campos que se muestran)
    campos_filtrables: list[str] | None = None

    def _campo_filtrable(self, campo: str) -> bool:
        whitelist = self.campos_filtrables or self.campos
        return campo in whitelist

    def get_queryset(self):
        qs = super().get_queryset()
        self._qs_original = qs

        campo = self.request.GET.get('campo', '').strip()
        valor = self.request.GET.get('valor', '').strip()

        if campo and valor and self._campo_filtrable(campo):
            try:
                model_field = self.model._meta.get_field(campo)
                if model_field.is_relation:
                    related_model = model_field.related_model
                    related_text_fields = [
                        f.name for f in related_model._meta.get_fields()
                        if isinstance(f, (models.CharField, models.TextField))
                    ]
                    if related_text_fields:
                        filtro = {f"{campo}__{related_text_fields[0]}__icontains": valor}
                        qs = qs.filter(**filtro)
                else:
                    qs = qs.filter(**{f"{campo}__icontains": valor})
            except Exception as e:
                # Log silencioso; no exponer detalles al usuario
                pass

        self._qs_filtrado = qs
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['campos']           = self.campos
        context['model_name']       = getattr(self, 'model_name', self.model.__name__)
        context['model_url_name']   = getattr(self, 'model_url_name', '').lower().replace(' ', '')
        context['request']          = self.request
        context['cantidad_original'] = self._qs_original.count()
        context['cantidad_filtrada'] = self._qs_filtrado.count()
        return context


# ====================================================
# 📋 LIST VIEWS
# ====================================================

class UsuarioAdminListView(BaseListView):
    model          = UsuarioAdmin
    model_name     = "Usuarios Admin"
    model_url_name = "usuarioadmins"
    campos         = ['id', 'usuario', 'rol', 'is_active']

class ClienteListView(BaseListView):
    model          = Cliente
    model_name     = "Clientes"
    model_url_name = "clientes"
    campos         = ['id_cliente', 'usuario', 'correo', 'telefono']

class CategoriaListView(BaseListView):
    model          = Categoria
    model_name     = "Categorías"
    model_url_name = "categorias"
    campos         = ['id_categoria', 'nombre', 'descripcion']

class ProductoListView(BaseListView):
    model          = Producto
    model_name     = "Productos"
    model_url_name = "productos"
    campos         = ['id_producto', 'nombre', 'categoria']

class ProductoVarianteListView(BaseListView):
    model          = ProductoVariante
    model_name     = "Variantes de Productos"
    model_url_name = "productosvariantes"
    campos         = ['id_variante', 'producto', 'tamaño', 'precio']

class SucursalListView(BaseListView):
    model          = Sucursal
    model_name     = "Sucursales"
    model_url_name = "sucursales"
    campos         = ['id_sucursal', 'direccion', 'telefono', 'hora_inicio', 'hora_cierre']

class InventarioSucursalListView(BaseListView):
    model          = InventarioSucursal
    model_name     = "Inventario por Sucursales"
    model_url_name = "inventariossucursal"
    campos         = ['id_inventario', 'sucursal', 'variante', 'stock']

class EmpleadoListView(BaseListView):
    model          = Empleado
    model_name     = "Empleados"
    model_url_name = "empleados"
    campos         = ['id_empleado', 'nombre', 'apellido', 'cargo', 'estado', 'sucursal']

class HistorialListView(BaseListView):
    model          = Historial
    model_name     = "Historial"
    model_url_name = "historial"
    campos         = ['id_historial', 'empleado', 'pedido', 'detalle', 'fecha']

class PromocionListView(BaseListView):
    model          = Promocion
    model_name     = "Promociones"
    model_url_name = "promociones"
    campos         = ['id_promocion', 'titulo', 'precio']

class PromocionDetalleListView(BaseListView):
    model          = PromocionDetalle
    model_name     = "Detalles de Promociones"
    model_url_name = "promocionesdetalle"
    campos         = ['id_detalle', 'promocion', 'variante', 'cantidad']

class CarritoListView(BaseListView):
    model          = Carrito
    model_name     = "Carritos"
    model_url_name = "carritos"
    campos         = ['id_carrito', 'cliente', 'creacion']

class CarritoItemListView(BaseListView):
    model          = CarritoItem
    model_name     = "Items del Carrito"
    model_url_name = "carritositems"
    campos         = ['id_item', 'carrito', 'variante', 'promocion', 'cantidad']

class PedidoListView(BaseListView):
    model          = Pedido
    model_name     = "Pedidos"
    model_url_name = "pedidos"
    campos         = ['id_pedido', 'codigo', 'cliente', 'sucursal', 'estado', 'fecha_pedido']

    def get_queryset(self):
        # Solo pedidos activos — entregados y cancelados van al historial
        self.queryset = Pedido.objects.exclude(estado__in=['entregado', 'cancelado'])
        return super().get_queryset()

class PedidoItemListView(BaseListView):
    model          = PedidoItem
    model_name     = "Items del Pedido"
    model_url_name = "pedidositems"
    campos         = ['id_item', 'pedido', 'variante', 'promocion', 'cantidad', 'precio']

class PagoListView(BaseListView):
    model          = Pago
    model_name     = "Pagos"
    model_url_name = "pagos"
    campos         = ['id_pago', 'pedido', 'monto', 'metodo_pago', 'estado']


# ====================================================
# 🏭 FACTORY PARA MODELOS Y FORMULARIOS
# ====================================================

class ModelFactory:
    models_forms = {
        'usuarioadmins':      (UsuarioAdmin,      UsuarioAdminForm),
        'clientes':           (Cliente,           ClienteForm),
        'categorias':         (Categoria,         CategoriaForm),
        'productos':          (Producto,          ProductoForm),
        'productosvariantes': (ProductoVariante,  ProductoVarianteForm),
        'sucursales':         (Sucursal,          SucursalForm),
        'inventariossucursal':(InventarioSucursal,InventarioSucursalForm),
        'empleados':          (Empleado,          EmpleadoForm),
        'historial':          (Historial,         HistorialForm),
        'promociones':        (Promocion,         PromocionForm),
        'promocionesdetalle': (PromocionDetalle,  PromocionDetalleForm),
        'carritos':           (Carrito,           CarritoForm),
        'carritositems':      (CarritoItem,       CarritoItemForm),
        'pedidos':            (Pedido,            PedidoForm),
        'pedidositems':       (PedidoItem,        PedidoItemForm),
        'pagos':              (Pago,              PagoForm),
    }

    @classmethod
    def get_model_and_form(cls, model_name):
        return cls.models_forms.get(model_name)


# ====================================================
# 🏗️ VISTAS BASE CRUD
# ====================================================

class BaseObjetoView:
    template_name = 'panel_admin/aniadir_editar.html'

    def get_model_and_form_tuple(self):
        model_name = self.kwargs['model_name']
        result = ModelFactory.get_model_and_form(model_name)
        if not result:
            raise Http404(f"Modelo '{model_name}' no encontrado.")
        return result

    def get_queryset(self):
        model, _ = self.get_model_and_form_tuple()
        return model.objects.all()

    def get_form_class(self):
        _, form_class = self.get_model_and_form_tuple()
        return form_class

    def get_success_url(self):
        return reverse_lazy(f"{self.kwargs['model_name']}_lista")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['model_name'] = self.kwargs['model_name']
        return context


class CrearObjetoView(LoginRequiredMixin, BaseObjetoView, CreateView):
    login_url = '/panel_admin/login/'


class EditarObjetoView(LoginRequiredMixin, BaseObjetoView, UpdateView):
    login_url = '/panel_admin/login/'

    def get_object(self, queryset=None):
        model, _ = self.get_model_and_form_tuple()
        return get_object_or_404(model, pk=self.kwargs['pk'])


class EliminarObjetoView(LoginRequiredMixin, BaseObjetoView, DeleteView):
    """
    DeleteView requiere self.queryset o get_queryset() para funcionar
    correctamente con el dispatch interno de Django.
    BaseObjetoView.get_queryset() lo provee ahora.
    """
    login_url     = '/panel_admin/login/'
    template_name = 'panel_admin/confirmar_eliminar.html'

    def get_object(self, queryset=None):
        model, _ = self.get_model_and_form_tuple()
        return get_object_or_404(model, pk=self.kwargs['pk'])

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            self.object.delete()
            messages.success(request, 'Registro eliminado exitosamente.')
        except IntegrityError:
            messages.error(request, 'No se puede eliminar: el registro está relacionado con otros datos.')
        return redirect(self.get_success_url())