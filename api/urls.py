from django.urls import path
from .views import *
from rest_framework.authtoken import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ==================== NUEVA ESTRUCTURA - CRUD ====================
    
    # USUARIOS
    path('usuarios-admin/', UsuarioAdminListCreate.as_view(), name='usuarios-admin'),
    path('clientes/', ClienteListCreateUpdate.as_view(), name='clientes'),
    
    # NEGOCIO - PRODUCTOS
    path('categorias/', CategoriaListCreate.as_view(), name='categorias'),
    path('productos/', ProductoListCreate.as_view(), name='productos'),
    path('productos-variantes/', ProductoVarianteListCreate.as_view(), name='productos-variantes'),
    
    # NEGOCIO - SUCURSALES Y EMPLEADOS
    path('sucursales/', SucursalListCreate.as_view(), name='sucursales'),
    path('empleados/', EmpleadoListCreate.as_view(), name='empleados'),
    path('historiales/', HistorialListCreate.as_view(), name='historiales'),
    path('inventarios-sucursal/', InventarioSucursalListCreate.as_view(), name='inventarios-sucursal'),
    
    # PROMOCIONES
    path('promociones/', PromocionListCreate.as_view(), name='promociones'),
    path('promociones-detalle/', PromocionDetalleListCreate.as_view(), name='promociones-detalle'),
    
    # CARRITO
    path('carritos/', CarritoListCreate.as_view(), name='carrito-list-create'),
    path('carritos/limpiar/', LimpiarCarritoView.as_view(), name='carrito-limpiar'),
    path('carritos-items/', CarritoItemListCreate.as_view(), name='carritos-items'),
    path('carritos-items/<int:id_item>/', CarritoItemDetail.as_view(), name='carrito-item-detail'),
    
    # PEDIDOS
    path('pedidos/', PedidoListCreate.as_view(), name='pedidos'),
    path('pedidos-items/', PedidoItemListCreate.as_view(), name='pedidos-items'),
    
    # PAGOS
    path('pagos/', PagoListCreate.as_view(), name='pagos'),
    
    # ==================== AUTENTICACIÓN ====================
    
    path('registro/', RegistroView.as_view(), name='registro'),
    path('login/', LoginView.as_view(), name='login'),
    path('refresh/', RefreshTokenView.as_view(), name='refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('status/', Status.as_view(), name='status'),
    path('api-token-auth/', views.obtain_auth_token),
    
    # ==================== BÚSQUEDAS ====================
    
    # USUARIOS
    path('clientes/<str:columna>/<str:valor_a_buscar>/', ClienteSearchView.as_view(), name='search-cliente'),
    path('usuarios-admin/<str:columna>/<str:valor_a_buscar>/', UsuarioAdminSearchView.as_view(), name='search-usuario-admin'),
    
    # NEGOCIO - PRODUCTOS
    path('categorias/<str:columna>/<str:valor_a_buscar>/', CategoriaSearchView.as_view(), name='search-categoria'),
    path('productos/<str:columna>/<str:valor_a_buscar>/', ProductoSearchView.as_view(), name='search-producto'),
    path('productos-variantes/<str:columna>/<str:valor_a_buscar>/', ProductoVarianteSearchView.as_view(), name='search-producto-variante'),
    
    # NEGOCIO - SUCURSALES Y EMPLEADOS
    path('sucursales/<str:columna>/<str:valor_a_buscar>/', SucursalSearchView.as_view(), name='search-sucursal'),
    path('empleados/<str:columna>/<str:valor_a_buscar>/', EmpleadoSearchView.as_view(), name='search-empleado'),
    path('historiales/<str:columna>/<str:valor_a_buscar>/', HistorialSearchView.as_view(), name='search-historial'),
    path('inventarios-sucursal/<str:columna>/<str:valor_a_buscar>/', InventarioSucursalSearchView.as_view(), name='search-inventario-sucursal'),
    
    # PROMOCIONES
    path('promociones/<str:columna>/<str:valor_a_buscar>/', PromocionSearchView.as_view(), name='search-promocion'),
    path('promociones-detalle/<str:columna>/<str:valor_a_buscar>/', PromocionDetalleSearchView.as_view(), name='search-promocion-detalle'),
    
    # CARRITO
    path('carritos/<str:columna>/<str:valor_a_buscar>/', CarritoSearchView.as_view(), name='search-carrito'),
    path('carritos-items/<str:columna>/<str:valor_a_buscar>/', CarritoItemSearchView.as_view(), name='search-carrito-item'),
    
    # PEDIDOS
    path('pedidos/<str:columna>/<str:valor_a_buscar>/', PedidoSearchView.as_view(), name='search-pedido'),
    path('pedidos-items/<str:columna>/<str:valor_a_buscar>/', PedidoItemSearchView.as_view(), name='search-pedido-item'),
    
    # PAGOS
    path('pagos/<str:columna>/<str:valor_a_buscar>/', PagoSearchView.as_view(), name='search-pago'),
    
    # MERCADO PAGO
    path('mercadopago/preference/', MercadoPagoPreferenceView.as_view(), name='mercadopago-preference'),
    path('mercadopago/confirmar-pago-manual/', ConfirmarPagoManualView.as_view(), name='confirmar-pago-manual'),
    path('mercadopago/verificar-checkout/', VerificarCheckoutView.as_view(), name='verificar-checkout'),
    path('mercadopago-webhook/', MercadoPagoWebhookView.as_view(), name='mercadopago-webhook'),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)