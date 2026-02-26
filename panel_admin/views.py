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
from django.db.models.functions import TruncMonth, TruncDay, TruncHour, Concat, Coalesce
from django.db.models import Value, Count, Sum, Avg, F, Q, ExpressionWrapper, DurationField, FloatField, Subquery, OuterRef
import locale
from django.utils.timezone import now

locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
hoy = timezone.now()
meses = [(hoy - timedelta(days=30 * i)).strftime("%B %Y") for i in range(11, -1, -1)]

# ====================================================
# 📊 VISTAS DE ESTADÍSTICAS (DASHBOARDS)
# ====================================================

@login_required(login_url='/panel_admin/login/')
def vista_admin_ventas(request):
    # ultimos 12 meses
    hace_12_meses = hoy - timedelta(days=365)
    ventas_mensuales = (
        Pedido.objects
        .filter(fecha_pedido__gte=hace_12_meses)
        .annotate(mes=TruncMonth('fecha_pedido'))
        .values('mes')
        .annotate(
            total_ventas=Count('id_pedido'),
            total_ingresos=Sum('pago__monto', default=0)
        )
        .order_by('mes')
    )

    data_ventas = []
    for mes in meses:
        venta_mes = next((venta for venta in ventas_mensuales if venta['mes'].strftime("%B %Y") == mes), None)
        total_ventas = venta_mes['total_ventas'] if venta_mes else 0
        total_ingresos = float(venta_mes['total_ingresos']) if venta_mes and venta_mes['total_ingresos'] else 0
        data_ventas.append(f"{total_ventas} - S/.{total_ingresos:.2f}")

    # metodos pagos
    metodos_pago = Pago.objects.values('metodo_pago').annotate(cantidad=Count('id_pago'))
    data_pagos = [[pago['metodo_pago'], pago['cantidad']] for pago in metodos_pago]

    # top dias
    top_dias = Pedido.objects \
        .annotate(dia=TruncDay('fecha_pedido')) \
        .values('dia') \
        .annotate(total_ventas=Count('id_pedido')) \
        .order_by('-total_ventas')[:4]

    top_dias_data = [{"dia": dia['dia'].strftime('%A'), "total_ventas": dia['total_ventas']} for dia in top_dias]

    # Horas con más ventas (Top 4)
    top_horas = Pedido.objects \
        .annotate(hora=TruncHour('fecha_pedido')) \
        .values('hora') \
        .annotate(total_ventas=Count('id_pedido')) \
        .order_by('-total_ventas')[:4]

    top_horas_data = [{"hora": hora['hora'].strftime('%H:%M'), "total_ventas": hora['total_ventas']} for hora in top_horas]

    # Ingresos del mes actual
    inicio_mes = timezone.now().replace(day=1)
    fin_mes = inicio_mes + timedelta(days=31)
    ingresos_mes = Pago.objects.filter(pedido__fecha_pedido__range=(inicio_mes, fin_mes)).aggregate(Sum('monto'))['monto__sum'] or 0
    ingresos_mes = round(ingresos_mes, 2)

    # Costo promedio de venta
    costo_promedio_venta = Pago.objects.aggregate(Avg('monto'))['monto__avg'] or 0
    costo_promedio_venta = round(costo_promedio_venta, 2)

    return render(request, 'panel_admin/admin_ventas.html', {
        'data_ventas': json.dumps(data_ventas),
        'meses': json.dumps(meses),
        'data_pagos': json.dumps(data_pagos),
        'top_dias_data': top_dias_data,
        'top_horas_data': top_horas_data,
        'ingresos_mes': ingresos_mes,
        'costo_promedio_venta': costo_promedio_venta,
    })

@login_required(login_url='/panel_admin/login/')
def vista_admin_clientes(request):
    # 1. Clientes por cada mes en el último año
    hoy = timezone.now()
    clientes_por_cada_mes_ultimo_anio = [
        Pedido.objects.filter(
            fecha_pedido__year=hoy.year if hoy.month >= mes else hoy.year - 1,
            fecha_pedido__month=mes
        ).values('cliente_id').distinct().count()
        for mes in range(1, 13)
    ]
    
    # 2. Porcentaje de retención de clientes
    total_clientes = Cliente.objects.count()
    clientes_recurrentes = Cliente.objects.filter(
        pedido__isnull=False
    ).annotate(num_pedidos=Count('pedido')).filter(num_pedidos__gt=1).count()
    porcentaje_retencion = (clientes_recurrentes / total_clientes * 100) if total_clientes else 0

    # 3. Total de clientes
    total_clientes = Cliente.objects.count()
    
    # 4. Nuevos clientes en el mes actual
    inicio_mes = now().replace(day=1)

    subquery = Pedido.objects.filter(
        cliente_id=OuterRef('cliente_id'),
        fecha_pedido__lt=inicio_mes
    ).values('cliente_id')

    clientes_nuevos_mes = Pedido.objects.filter(
        fecha_pedido__gte=inicio_mes, 
        fecha_pedido__lt=now(),
    ).exclude(
        cliente_id__in=Subquery(subquery)
    ).values('cliente_id').distinct().count()

    # 5. Clientes con más pedidos
    clientes_mas_frecuentes = (
        Cliente.objects.annotate(total_pedidos=Count('pedido'))
        .order_by('-total_pedidos')[:4]
        .values_list('usuario', 'total_pedidos')
    )

    return render(request, 'panel_admin/admin_clientes.html', {
        'clientes_por_cada_mes_ultimo_anio': json.dumps(clientes_por_cada_mes_ultimo_anio),
        'meses': json.dumps(meses),
        'porcentaje_retencion': round(porcentaje_retencion, 2),
        'total_clientes': total_clientes,
        'clientes_nuevos_mes': clientes_nuevos_mes,
        'clientes_mas_frecuentes': list(clientes_mas_frecuentes)
    })

@login_required(login_url='/panel_admin/login/')
def vista_admin_empleados(request):
    hoy = timezone.now()

    # 1. Empleados con más ventas en los últimos 12 meses
    data_empleados_mas_ventas_query = (
        Historial.objects
        .filter(pedido__fecha_pedido__gte=hoy.replace(year=hoy.year - 1))
        .values('empleado__nombre', 'empleado__apellido')
        .annotate(
            total_pedidos=Count('pedido'),
            nombre_completo=Concat('empleado__nombre', Value(' '), 'empleado__apellido')
        )
        .order_by('-total_pedidos')[:12]
        .values_list('nombre_completo', 'total_pedidos')
    )

    data_empleados_mas_ventas = [
        [nombre_completo, total_pedidos] for nombre_completo, total_pedidos in data_empleados_mas_ventas_query
    ]

    # 2. Empleados que han generado más ingresos en todo el tiempo
    empleados_mas_ingresos = (
        Historial.objects
        .values('empleado__nombre')
        .annotate(total_ingresos=Sum('pedido__pago__monto'))
        .order_by('-total_ingresos')[:4]
        .values_list('empleado__nombre', 'total_ingresos')
    )

    empleados_mas_ingresos = [
        (nombre, total_ingresos if total_ingresos is not None else 0)
        for nombre, total_ingresos in empleados_mas_ingresos
    ]
    
    # 3. Empleados más eficaces (menor tiempo entre fecha_pedido y fecha_entrega)
    empleados_mas_eficaces_query = (
        Historial.objects
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
        [
            nombre_completo, 
            (promedio_tiempo.total_seconds() / 60) if promedio_tiempo is not None else 0
        ]
        for nombre_completo, promedio_tiempo in empleados_mas_eficaces_query
    ]

    # 4. Estados de los empleados
    estado_empleados = [
        ["Activo", Empleado.objects.filter(estado="activo").count()],
        ["Inactivo", Empleado.objects.filter(estado="inactivo").count()],
        ["Vacaciones", Empleado.objects.filter(estado="vacaciones").count()],
    ]
    
    # 5. Ventas promedio por empleado
    total_pedidos = Pedido.objects.count()
    total_empleados = Empleado.objects.count()

    ventas_promedio_por_empleado = round(
        total_pedidos / max(total_empleados, 1), 
        2
    )

    # 6. Tiempo promedio entre pedidos.fecha_pedido y pedidos.fecha_entrega en horas
    tiempo_promedio_pedido = (
        Pedido.objects.annotate(
            tiempo=ExpressionWrapper(
                F('fecha_entrega') - F('fecha_pedido'),
                output_field=DurationField() 
            )
        )
        .aggregate(
            total_tiempo=Sum('tiempo'),
            total_pedidos=Count('id_pedido')
        )
    )

    if tiempo_promedio_pedido['total_tiempo'] and tiempo_promedio_pedido['total_pedidos']:
        promedio_segundos = tiempo_promedio_pedido['total_tiempo'].total_seconds()
        tiempo_promedio_pedido = (promedio_segundos / 3600) / tiempo_promedio_pedido['total_pedidos']
        tiempo_promedio_pedido = round(tiempo_promedio_pedido, 2)
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
        .values('sucursal__direccion')
        .annotate(total_empleados=Count('id_empleado'))
        .order_by('-total_empleados')
        .values_list('sucursal__direccion', 'total_empleados')
    )

    ganancias_promedio_sucursal = Pago.objects.aggregate(promedio_ganancias=Avg('monto'))['promedio_ganancias'] or 0

    pedidos_promedio_sucursal = Pedido.objects.aggregate(promedio_pedidos=Avg('id_pedido'))['promedio_pedidos'] or 0

    return render(request, 'panel_admin/admin_sucursales.html', {
        'data_ventas_sucursal': json.dumps(data_ventas_sucursal),
        'data_clientes_sucursal': data_clientes_sucursal,
        'data_empleados_sucursal': data_empleados_sucursal,
        'ganancias_promedio_sucursal': round(ganancias_promedio_sucursal, 2),
        'pedidos_promedio_sucursal': round(pedidos_promedio_sucursal, 2),
    })

@login_required(login_url='/panel_admin/login/')
def vista_admin_productos(request):
    # Productos más vendidos
    productos_mas_vendidos = list(
        PedidoItem.objects.filter(variante__isnull=False)
        .values('variante__producto__nombre', 'variante__tamaño')
        .annotate(total_vendido=Sum('cantidad'))
        .order_by('-total_vendido')[:8]
        .values_list('variante__producto__nombre', 'total_vendido')
    )

    # Promociones más vendidas
    promociones_mas_vendidas = list(
        PedidoItem.objects.filter(promocion__isnull=False)
        .values('promocion__titulo')
        .annotate(total_vendido=Sum('cantidad'))
        .order_by('-total_vendido')[:4]
        .values_list('promocion__titulo', 'total_vendido')
    )

    # 🔥 NUEVO: Productos con stock bajo
    stock_bajo = list(
        ProductoVariante.objects.filter(stock__lt=10)
        .values('producto__nombre', 'tamaño', 'stock')
        .order_by('stock')[:10]
    )

    # Total de productos
    total_productos = Producto.objects.count()
    
    # Total de promociones
    total_promociones = Promocion.objects.count()

    return render(request, 'panel_admin/admin_productos.html', {
        'productos_mas_vendidos': json.dumps(productos_mas_vendidos),
        'promociones_mas_vendidas': json.dumps(promociones_mas_vendidas),
        'stock_bajo': stock_bajo,  # ← AGREGAR
        'total_productos': total_productos,
        'total_promociones': total_promociones,
    })

# ====================================================
# 🔐 LOGIN
# ====================================================

def login_view(request):
    if request.method == 'POST':
        username = request.POST['usuario']
        password = request.POST['contrasena']

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'admin_ventas')
            return redirect(next_url)
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')

    return render(request, 'panel_admin/login.html')

# ====================================================
# 📋 VISTAS BASE PARA LISTADOS
# ====================================================

class BaseListView(LoginRequiredMixin, ListView):
    login_url = '/panel_admin/login/'
    template_name = 'panel_admin/lista.html'
    context_object_name = 'objetos'
    paginate_by = 7

    def get_queryset(self):
        self.queryset_original = super().get_queryset()
        queryset = self.queryset_original
        campo = self.request.GET.get('campo')
        valor = self.request.GET.get('valor')

        if campo and valor:
            try:
                model_field = self.model._meta.get_field(campo)
                
                if model_field.is_relation:
                    related_model = model_field.related_model
                    related_fields = [
                        f.name for f in related_model._meta.get_fields() if isinstance(f, (models.CharField, models.TextField))
                    ]
                    if related_fields:
                        related_field = f"{campo}__{related_fields[0]}"
                        filtro = {f"{related_field}__icontains": valor}
                    else:
                        raise ValueError(f"No se encontró un campo de texto en el modelo relacionado para '{campo}'.")
                else:
                    filtro = {f"{campo}__icontains": valor}
                queryset = queryset.filter(**filtro)
            except Exception as e:
                print(f"Error en el filtro: {e}")

        self.queryset_filtrado = queryset
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['campos'] = self.campos
        context['model_name'] = getattr(self, 'model_name', self.model.__name__)
        context['model_url_name'] = getattr(self, 'model_url_name', getattr(self, 'model_name', '').lower().replace(' ', ''))
        context['request'] = self.request
        context['cantidad_original'] = self.queryset_original.count()
        context['cantidad_filtrada'] = self.queryset_filtrado.count()
        return context

# ====================================================
# 📋 LIST VIEWS - NUEVA ESTRUCTURA
# ====================================================

class UsuarioAdminListView(BaseListView):
    model = UsuarioAdmin
    model_name = "Usuarios Admin"
    model_url_name = "usuarioadmins"
    campos = ['id', 'usuario', 'rol', 'is_active']

class ClienteListView(BaseListView):
    model = Cliente
    model_name = "Clientes"
    model_url_name = "clientes"
    campos = ['id_cliente', 'usuario', 'correo', 'telefono']

class CategoriaListView(BaseListView):
    model = Categoria
    model_name = "Categorías"
    model_url_name = "categorias"
    campos = ['id_categoria', 'nombre', 'descripcion']

class ProductoListView(BaseListView):
    model = Producto
    model_name = "Productos"
    model_url_name = "productos"
    campos = ['id_producto', 'nombre', 'categoria']

class ProductoVarianteListView(BaseListView):
    model = ProductoVariante
    model_name = "Variantes de Productos"
    model_url_name = "productosvariantes"
    campos = ['id_variante', 'producto', 'tamaño', 'precio', 'stock']

class SucursalListView(BaseListView):
    model = Sucursal
    model_name = "Sucursales"
    model_url_name = "sucursales"
    campos = ['id_sucursal', 'direccion', 'telefono', 'hora_inicio', 'hora_cierre']

class EmpleadoListView(BaseListView):
    model = Empleado
    model_name = "Empleados"
    model_url_name = "empleados"
    campos = ['id_empleado', 'nombre', 'apellido', 'cargo', 'estado', 'sucursal']

class HistorialListView(BaseListView):
    model = Historial
    model_name = "Historial"
    model_url_name = "historial"
    campos = ['id_historial', 'empleado', 'pedido', 'detalle', 'fecha']

class PromocionListView(BaseListView):
    model = Promocion
    model_name = "Promociones"
    model_url_name = "promociones"
    campos = ['id_promocion', 'titulo', 'precio']

class PromocionDetalleListView(BaseListView):
    model = PromocionDetalle
    model_name = "Detalles de Promociones"
    model_url_name = "promocionesdetalle"
    campos = ['id_detalle', 'promocion', 'variante', 'cantidad']

class CarritoListView(BaseListView):
    model = Carrito
    model_name = "Carritos"
    model_url_name = "carritos"
    campos = ['id_carrito', 'cliente', 'creacion']

class CarritoItemListView(BaseListView):
    model = CarritoItem
    model_name = "Items del Carrito"
    model_url_name = "carritositems"
    campos = ['id_item', 'carrito', 'variante', 'promocion', 'cantidad']

class PedidoListView(BaseListView):
    model = Pedido
    model_name = "Pedidos"
    model_url_name = "pedidos"
    campos = ['id_pedido', 'codigo', 'cliente', 'sucursal', 'estado', 'fecha_pedido']

class PedidoItemListView(BaseListView):
    model = PedidoItem
    model_name = "Items del Pedido"
    model_url_name = "pedidositems"
    campos = ['id_item', 'pedido', 'variante', 'promocion', 'cantidad', 'precio']

class PagoListView(BaseListView):
    model = Pago
    model_name = "Pagos"
    model_url_name = "pagos"
    campos = ['id_pago', 'pedido', 'monto', 'metodo_pago', 'estado']

# ====================================================
# 🏭 FACTORY PARA MODELOS Y FORMULARIOS
# ====================================================

class ModelFactory:
    models_forms = {
        'usuarioadmins': (UsuarioAdmin, UsuarioAdminForm),
        'clientes': (Cliente, ClienteForm),
        'categorias': (Categoria, CategoriaForm),
        'productos': (Producto, ProductoForm),
        'productosvariantes': (ProductoVariante, ProductoVarianteForm),
        'sucursales': (Sucursal, SucursalForm),
        'empleados': (Empleado, EmpleadoForm),
        'historial': (Historial, HistorialForm),
        'promociones': (Promocion, PromocionForm),
        'promocionesdetalle': (PromocionDetalle, PromocionDetalleForm),
        'carritos': (Carrito, CarritoForm),
        'carritositems': (CarritoItem, CarritoItemForm),
        'pedidos': (Pedido, PedidoForm),
        'pedidositems': (PedidoItem, PedidoItemForm),
        'pagos': (Pago, PagoForm),
    }

    @classmethod
    def get_model_and_form(cls, model_name):
        return cls.models_forms.get(model_name)

# ====================================================
# 🏗️ VISTAS BASE PARA CRUD
# ====================================================

class BaseObjetoView:
    template_name = 'panel_admin/aniadir_editar.html'

    def get_model(self):
        model_name = self.kwargs['model_name']
        model_and_form = ModelFactory.get_model_and_form(model_name)
        if not model_and_form:
            raise Http404(f"Modelo {model_name} no encontrado.")
        return model_and_form

    def get_form_class(self):
        _, form_class = self.get_model()
        return form_class

    def get_success_url(self):
        model_name = self.kwargs["model_name"]
        return reverse_lazy(f'{model_name}_lista') 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['model_name'] = self.kwargs['model_name']
        return context

class CrearObjetoView(BaseObjetoView, CreateView):
    pass

class EditarObjetoView(BaseObjetoView, UpdateView):
    def get_object(self):
        model, _ = self.get_model()
        return get_object_or_404(model, pk=self.kwargs['pk'])

class EliminarObjetoView(BaseObjetoView, DeleteView):
    template_name = 'panel_admin/confirmar_eliminar.html' 

    def get_object(self):
        model, _ = self.get_model()
        return get_object_or_404(model, pk=self.kwargs['pk'])

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            self.object.delete()
            messages.success(request, 'Registro eliminado exitosamente.')
        except IntegrityError:
            messages.error(request, 'No se puede eliminar el registro porque está relacionado con otros datos.')
        return redirect(self.get_success_url())