from django.urls import path
from .views import *

urlpatterns = [
    path('login/', login_view, name='login'),
    path('ventas/', vista_admin_ventas, name='admin_ventas'),
    path('empleados/', vista_admin_empleados, name='admin_empleados'),
    path('clientes/', vista_admin_clientes, name='admin_clientes'),
    path('sucursales/', vista_admin_sucursales, name='admin_surcursales'),
    path('productosprima/', vista_admin_pprima, name='admin_productosprima'),
    #path('productosventa/', vista_admin_pventa, name='admin_productosventa'),

    path('categorias_lista/', CategoriaListView.as_view(), name='categorias_lista'),
    path('sucursales_lista/', SucursalListView.as_view(), name='sucursales_lista'),
    path('empleados_lista/', EmpleadoListView.as_view(), name='empleados_lista'),
    path('areas_lista/', AreaListView.as_view(), name='areas_lista'),
    path('productosventa_lista/', ProductoVentaListView.as_view(), name='productosventa_lista'),
    path('productosprima_lista/', ProductoPrimaListView.as_view(), name='productosprima_lista'),
    path('paquetes_lista/', PaqueteListView.as_view(), name='paquetes_lista'),
    path('usuarioadmins_lista/', UsuarioAdminListView.as_view(), name='usuarioadmins_lista'),
    path('pedidos_lista/', PedidoListView.as_view(), name='pedidos_lista'),
    path('detallepedido/', DetallePedidoListView.as_view(), name='detallepedido_lista'),
    path('pagos_lista/', PagoListView.as_view(), name='pagos_lista'),
    path('historial_lista/', HistorialListView.as_view(), name='historial_lista'),
    path('cliente_lista/', ClienteListView.as_view(), name='clientes_lista'),
    path('repertorio_lista/', RepertorioListView.as_view(), name='repertorios_lista'),
    path('detalles_repertorio/', DetalleRepertorioListView.as_view(), name='detallesrepertorio_lista'),
    path('carritos/', CarritoListView.as_view(), name='carritos_lista'),

    path('crear/<str:model_name>/', CrearObjetoView.as_view(), name='crear_objeto'),
    path('editar/<str:model_name>/<int:pk>/', EditarObjetoView.as_view(), name='editar_objeto'),
    path('eliminar/<str:model_name>/<int:pk>/', EliminarObjetoView.as_view(), name='eliminar_objeto'),
]
