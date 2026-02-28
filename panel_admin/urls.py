from django.urls import path
from .views import *

urlpatterns = [
    # ==================== LOGIN ====================
    path('login/', login_view, name='login'),
    
    # ==================== DASHBOARDS (ESTADÍSTICAS) ====================
    path('ventas/', vista_admin_ventas, name='admin_ventas'),
    path('empleados/', vista_admin_empleados, name='admin_empleados'),
    path('clientes/', vista_admin_clientes, name='admin_clientes'),
    path('sucursales/', vista_admin_sucursales, name='admin_sucursales'),
    path('productos/', vista_admin_productos, name='admin_productos'),
    
    # ==================== LISTAS (CRUD) - NUEVA ESTRUCTURA ====================
    
    # USUARIOS
    path('usuarioadmins_lista/', UsuarioAdminListView.as_view(), name='usuarioadmins_lista'),
    path('clientes_lista/', ClienteListView.as_view(), name='clientes_lista'),
    
    # NEGOCIO - PRODUCTOS
    path('categorias_lista/', CategoriaListView.as_view(), name='categorias_lista'),
    path('productos_lista/', ProductoListView.as_view(), name='productos_lista'),
    path('productosvariantes_lista/', ProductoVarianteListView.as_view(), name='productosvariantes_lista'),
    
    # NEGOCIO - SUCURSALES Y EMPLEADOS
    path('sucursales_lista/', SucursalListView.as_view(), name='sucursales_lista'),
    path('inventariossucursal_lista/', InventarioSucursalListView.as_view(), name='inventariossucursal_lista'),
    path('empleados_lista/', EmpleadoListView.as_view(), name='empleados_lista'),
    path('historial_lista/', HistorialListView.as_view(), name='historial_lista'),
    
    # PROMOCIONES
    path('promociones_lista/', PromocionListView.as_view(), name='promociones_lista'),
    path('promocionesdetalle_lista/', PromocionDetalleListView.as_view(), name='promocionesdetalle_lista'),
    
    # CARRITO
    path('carritos_lista/', CarritoListView.as_view(), name='carritos_lista'),
    path('carritositems_lista/', CarritoItemListView.as_view(), name='carritositems_lista'),
    
    # PEDIDOS
    path('pedidos_lista/', PedidoListView.as_view(), name='pedidos_lista'),
    path('pedidositems_lista/', PedidoItemListView.as_view(), name='pedidositems_lista'),
    
    # PAGOS
    path('pagos_lista/', PagoListView.as_view(), name='pagos_lista'),
    
    # ==================== CRUD GENÉRICO ====================
    path('crear/<str:model_name>/', CrearObjetoView.as_view(), name='crear_objeto'),
    path('editar/<str:model_name>/<int:pk>/', EditarObjetoView.as_view(), name='editar_objeto'),
    path('eliminar/<str:model_name>/<int:pk>/', EliminarObjetoView.as_view(), name='eliminar_objeto'),
]