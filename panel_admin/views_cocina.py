from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from api.models import Pedido, Sucursal, PedidoItem, Historial, Empleado
import json
from functools import wraps


# ── Estados reales del modelo Pedido ────────────────────────────────────────
# ESTADO_CHOICES del modelo:
# 'pendiente', 'confirmado', 'preparando', 'en_camino', 'entregado', 'cancelado'

ESTADOS_VALIDOS = ['pendiente', 'confirmado', 'preparando', 'en_camino', 'entregado', 'cancelado']

# Estados que excluimos del kanban (ya terminados)
ESTADOS_EXCLUIDOS = ['entregado', 'cancelado']

COLUMNAS_KANBAN = [
    {'key': 'pendiente',   'label': 'Pendiente',    'color': '#FDB913', 'icon': 'bi-clock-fill'},
    {'key': 'confirmado',  'label': 'Confirmado',   'color': '#9C27B0', 'icon': 'bi-check2-circle'},
    {'key': 'preparando',  'label': 'Preparando',   'color': '#FF6B35', 'icon': 'bi-fire'},
    {'key': 'en_camino',   'label': 'En Camino',    'color': '#2196F3', 'icon': 'bi-truck'},
]

# ── Decorator que devuelve JSON 401 en vez de redirect para APIs ─────────────
def login_requerido_json(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'ok': False, 'error': 'No autenticado.'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required(login_url='/panel_admin/login/')
def vista_cocina(request):
    sucursales = Sucursal.objects.all().values('id_sucursal', 'nombre', 'direccion')
    return render(request, 'panel_admin/cocina.html', {
        'columnas': COLUMNAS_KANBAN,
        'sucursales': list(sucursales),
    })


@login_requerido_json
def api_pedidos_cocina(request):
    """
    GET /panel_admin/cocina/pedidos/
    Devuelve pedidos activos (excluye entregados y cancelados).
    ?sucursal=<id>  ?tipo=delivery|recojo
    """
    qs = (
        Pedido.objects
        .exclude(estado__in=ESTADOS_EXCLUIDOS)
        .select_related('cliente', 'sucursal')
        .prefetch_related(
            'items__variante__producto',
            'items__promocion',
        )
        .order_by('fecha_pedido')
    )

    sucursal_id = request.GET.get('sucursal')
    if sucursal_id:
        qs = qs.filter(sucursal_id=sucursal_id)

    tipo = request.GET.get('tipo')
    if tipo in ['delivery', 'recojo']:
        qs = qs.filter(tipo_entrega=tipo)

    pedidos = []
    for p in qs:
        try:
            items = []
            # related_name='items' según el modelo
            for item in p.items.all():
                if item.variante:
                    nombre = f"{item.variante.producto.nombre} ({item.variante.tamaño})"
                elif item.promocion:
                    nombre = f"Promo: {item.promocion.titulo}"
                else:
                    nombre = "Item sin nombre"
                items.append({
                    'nombre':   nombre,
                    'cantidad': item.cantidad or 1,
                    'precio':   float(item.precio) if item.precio is not None else 0.0,
                })

            delta   = timezone.now() - p.fecha_pedido
            minutos = int(delta.total_seconds() / 60)

            pedidos.append({
                'id':                p.id_pedido,
                'codigo':            p.codigo or str(p.id_pedido),
                'estado':            p.estado,
                'tipo_entrega':      p.tipo_entrega or 'recojo',
                'cliente':           p.cliente.usuario if p.cliente else '—',
                'sucursal':          p.sucursal.nombre if p.sucursal else '—',
                'direccion_entrega': p.direccion or '',
                'costo_delivery':    float(p.costo_delivery) if p.costo_delivery else 0,
                'fecha_pedido':      p.fecha_pedido.strftime('%H:%M'),
                'minutos_esperando': minutos,
                'items':             items,
                'total':             sum(i['precio'] * i['cantidad'] for i in items),
            })

        except Exception as e:
            pedidos.append({
                'id':                p.id_pedido,
                'codigo':            str(p.codigo or p.id_pedido),
                'estado':            p.estado,
                'tipo_entrega':      'recojo',
                'cliente':           '—',
                'sucursal':          '—',
                'direccion_entrega': '',
                'costo_delivery':    0,
                'fecha_pedido':      '—',
                'minutos_esperando': 0,
                'items':             [{'nombre': f'Error al cargar: {str(e)}', 'cantidad': 1, 'precio': 0}],
                'total':             0,
            })

    return JsonResponse({'pedidos': pedidos, 'timestamp': timezone.now().isoformat()})


@login_requerido_json
@require_POST
def api_cambiar_estado_pedido(request, pk):
    """
    POST /panel_admin/cocina/pedidos/<pk>/estado/
    Body JSON: {"estado": "preparando"}

    Al marcar como 'entregado':
      - Crea registro en Historial con detalle='completado'
      - El pedido desaparece del kanban y de pedidos_lista
    """
    try:
        data   = json.loads(request.body)
        nuevo  = data.get('estado', '').strip()

        if nuevo not in ESTADOS_VALIDOS:
            return JsonResponse(
                {'ok': False, 'error': f'Estado "{nuevo}" no valido. Usa: {ESTADOS_VALIDOS}'},
                status=400
            )

        pedido         = get_object_or_404(Pedido, pk=pk)
        estado_anterior = pedido.estado
        pedido.estado  = nuevo
        pedido.save(update_fields=['estado'])

        historial_creado = False
        if nuevo == 'entregado' and estado_anterior != 'entregado':
            historial_creado = _crear_historial_entrega(pedido)

        return JsonResponse({
            'ok':              True,
            'estado':          nuevo,
            'id':              pk,
            'historial_creado': historial_creado,
        })

    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'JSON invalido.'}, status=400)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


def _crear_historial_entrega(pedido) -> bool:
    """
    Crea un Historial con detalle='completado' al entregar un pedido.
    Busca el primer empleado activo de la sucursal.
    Retorna True si se creó, False si falló.

    Restricciones del modelo Historial:
      - empleado: FK obligatorio (no nullable)
      - detalle:  choices = preparacion | en camino | entregando | completado
      - fecha:    DateField (solo fecha, no datetime)
    """
    try:
        empleado = None
        if pedido.sucursal_id:
            empleado = (
                Empleado.objects
                .filter(sucursal_id=pedido.sucursal_id, estado='activo')
                .first()
            )

        # Si no hay empleado activo en la sucursal, buscar cualquier empleado activo
        if not empleado:
            empleado = Empleado.objects.filter(estado='activo').first()

        # Si no hay ningún empleado activo en todo el sistema, no podemos crear el historial
        if not empleado:
            return False

        Historial.objects.create(
            empleado=empleado,
            pedido=pedido,
            detalle='completado',       # único valor válido para entrega
            fecha=timezone.now().date(), # DateField necesita solo fecha
        )
        return True

    except Exception:
        return False