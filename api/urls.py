from django.urls import path
from .views import *
from django.contrib.auth.views import LogoutView
from rest_framework.authtoken import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('areas/', AreaListCreate.as_view(), name='areas'),
    path('categorias/', CategoriaListCreate.as_view(), name='categorias'),
    path('clientes/', ClienteListCreateUpdate.as_view(), name='clientes'),
    path('sucursales/', SucursalListCreate.as_view(), name='sucursales'),
    path('pagos/', PagoListCreate.as_view(), name='pagos'),
    path('pedidos/', PedidoListCreate.as_view(), name='pedidos'),
    path('repertorios/', RepertorioListCreate.as_view(), name='repertorios'),
    path('productos-venta/', ProductoVentaListCreate.as_view(), name='productos-venta'),
    path('productos-prima/', ProductoPrimaListCreate.as_view(), name='productos-prima'),
    path('detalles-pedido/', DetallePedidoListCreate.as_view(), name='detalles-pedido'),
    path('paquetes/', PaqueteListCreate.as_view(), name='paquetes'),
    path('empleados/', EmpleadoListCreate.as_view(), name='empleados'),
    path('historiales/', HistorialListCreate.as_view(), name='historiales'),
    path('detalles-repertorio/', DetalleRepertorioListCreate.as_view(), name='detalles-repertorio'),
    path('carritos/', CarritoListCreate.as_view(), name='carritos'),

    path('registro/', RegistroView.as_view(), name='registro'),
    path('login/', LoginView.as_view(), name='login'),
    path('refresh/', RefreshTokenView.as_view(), name='refresh'),

    path('areas/<str:columna>/<str:valor_a_buscar>/', AreaSearchView.as_view(), name='search-area'),
    path('clientes/<str:columna>/<str:valor_a_buscar>/', ClienteSearchView.as_view(), name='search-cliente'),

    path('categorias/<str:columna>/<str:valor_a_buscar>/', CategoriaSearchView.as_view(), name='search-categoria'),
    path('sucursales/<str:columna>/<str:valor_a_buscar>/', SucursalSearchView.as_view(), name='search-sucursal'),
    path('pedidos/<str:columna>/<str:valor_a_buscar>//', PedidoSearchView.as_view(), name='search-pedido'),
    path('pagos/<str:columna>/<str:valor_a_buscar>/', PagoSearchView.as_view(), name='search-pago'),
    path('repertorios/<str:columna>/<str:valor_a_buscar>/', RepertorioSearchView.as_view(), name='search-repertorio'),
    path('detalles-repertorio/<str:columna>/<str:valor_a_buscar>/', DetalleRepertorioSearchView.as_view(), name='search-detalle-repertorio'),
    path('productos-venta/<str:columna>/<str:valor_a_buscar>/', ProductoVentaSearchView.as_view(), name='search-producto-venta'),
    path('productos-prima/<str:columna>/<str:valor_a_buscar>/', ProductoPrimaSearchView.as_view(), name='search-producto-prima'),
    path('detalles-pedido/<str:columna>/<str:valor_a_buscar>/', DetallePedidoSearchView.as_view(), name='search-detalle-pedido'),
    path('paquetes/<str:columna>/<str:valor_a_buscar>/', PaqueteSearchView.as_view(), name='search-paquete'),
    path('empleados/<str:columna>/<str:valor_a_buscar>/', EmpleadoSearchView.as_view(), name='search-empleado'),
    path('historiales/<str:columna>/<str:valor_a_buscar>/', HistorialSearchView.as_view(), name='search-historial'),
    path('carritos/<str:columna>/<str:valor_a_buscar>/', CarritoSearchView.as_view(), name='search-carrito'),

    path('api-token-auth/', views.obtain_auth_token),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('status/', Status.as_view(), name='status'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)