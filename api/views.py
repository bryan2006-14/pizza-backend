from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import *
from rest_framework.exceptions import NotFound, ValidationError
from django.apps import apps
from django.shortcuts import get_object_or_404

from .models import *
from .serializers import *
from django.db import transaction


# ====================================================
# 🔐 AUTENTICACIÓN Y TOKENS
# ====================================================

def get_tokens_for_user(cliente):
    refresh = RefreshToken.for_user(cliente)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


# ====================================================
# 📦 BASE GENÉRICA PARA LIST/CREATE
# ====================================================

class ListCreateView(generics.ListCreateAPIView):
    serializer_class = None
    queryset = None

    def get_queryset(self):
        model = self.serializer_class.Meta.model
        return model.objects.all()


# ====================================================
# 📋 CRUD PRINCIPALES - NUEVA ESTRUCTURA
# ====================================================

# === USUARIOS ===
class UsuarioAdminListCreate(ListCreateView):
    serializer_class = UsuarioAdminSerializer
    permission_classes = [IsAuthenticated]

class ClienteListCreateUpdate(generics.ListCreateAPIView):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [AllowAny()]
        return [IsAuthenticated()]

    def put(self, request, *args, **kwargs):
        cliente_id = request.data.get('id_cliente')
        if not cliente_id:
            return Response({"error": "El id_cliente es obligatorio."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cliente = Cliente.objects.get(id_cliente=cliente_id)
        except Cliente.DoesNotExist:
            return Response({"error": "Cliente no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(cliente, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# === NEGOCIO - PRODUCTOS ===
class CategoriaListCreate(ListCreateView):
    serializer_class = CategoriaSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

class ProductoListCreate(ListCreateView):
    serializer_class = ProductoSerializer
    permission_classes = [AllowAny]

class ProductoVarianteListCreate(ListCreateView):
    serializer_class = ProductoVarianteSerializer
    permission_classes = [AllowAny]


# === NEGOCIO - SUCURSALES Y EMPLEADOS ===
class SucursalListCreate(ListCreateView):
    serializer_class = SucursalSerializer
    permission_classes = [AllowAny]

class EmpleadoListCreate(ListCreateView):
    serializer_class = EmpleadoSerializer
    permission_classes = [IsAuthenticated]

class InventarioSucursalListCreate(ListCreateView):
    serializer_class = InventarioSucursalSerializer
    permission_classes = [AllowAny] # O IsAuthenticated dependiendo de tu flujo

class HistorialListCreate(ListCreateView):
    serializer_class = HistorialSerializer
    permission_classes = [IsAuthenticated]


# === PROMOCIONES ===
class PromocionListCreate(ListCreateView):
    serializer_class = PromocionSerializer
    permission_classes = [AllowAny]

class PromocionDetalleListCreate(ListCreateView):
    serializer_class = PromocionDetalleSerializer
    permission_classes = [IsAuthenticated]


# === CARRITO ===
class CarritoListCreate(generics.ListCreateAPIView):
    queryset = Carrito.objects.all()
    serializer_class = CarritoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Filtrar por cliente si se especifica
        cliente_id = self.request.query_params.get('cliente_id')
        if cliente_id:
            return Carrito.objects.filter(cliente_id=cliente_id)
        return Carrito.objects.all()

class CarritoItemListCreate(generics.ListCreateAPIView):
    queryset = CarritoItem.objects.all()
    serializer_class = CarritoItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Filtrar por carrito si se especifica
        carrito_id = self.request.query_params.get('carrito_id')
        if carrito_id:
            return CarritoItem.objects.filter(carrito_id=carrito_id)
        return CarritoItem.objects.all()

    def delete(self, request, *args, **kwargs):
        item_id = request.data.get('id_item')
        if item_id:
            try:
                item = CarritoItem.objects.get(id_item=item_id)
                item.delete()
                return Response({"message": "Item eliminado del carrito con éxito."}, status=status.HTTP_204_NO_CONTENT)
            except CarritoItem.DoesNotExist:
                return Response({"error": "Item no encontrado en el carrito."}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({"error": "No se proporcionó un id_item."}, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        serializer.save()

class CarritoItemDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = CarritoItem.objects.all()
    serializer_class = CarritoItemSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id_item'


# === PEDIDOS ===
class PedidoListCreate(generics.ListCreateAPIView):
    queryset = Pedido.objects.all().order_by('-fecha_pedido')
    serializer_class = PedidoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Filtrar por cliente si se especifica
        cliente_id = self.request.query_params.get('cliente_id')
        if cliente_id:
            return Pedido.objects.filter(cliente_id=cliente_id).order_by('-fecha_pedido')
        return Pedido.objects.all().order_by('-fecha_pedido')
        
    def perform_create(self, serializer):
        # El guardado del pedido ahora disparará la creación de PedidoItems,
        # los cuales tienen la lógica de descuento de stock en su método save()
        pedido = serializer.save()
        
        # Opcional: Si tienes un carrito activo para este cliente, procesamos sus items
        # Nota: Asegúrate de que el carrito tenga un campo 'activo' o maneja la lógica según tu app
        carrito = Carrito.objects.filter(cliente=pedido.cliente).last()

        if carrito:
            items = CarritoItem.objects.filter(carrito=carrito)
            
            # Verificación de stock por sucursal
            for item in items:
                # 1. Verificar el item principal (si es variante simple)
                if item.variante:
                    inv = InventarioSucursal.objects.filter(sucursal=pedido.sucursal, variante=item.variante).first()
                    if not inv or inv.stock < item.cantidad:
                        raise ValidationError({'error': f'Stock insuficiente para {item.variante.producto.nombre}'})
                
                # 2. Verificar la promoción (detalles fijos)
                elif item.promocion:
                    detalles_fijos = PromocionDetalle.objects.filter(promocion=item.promocion, variante__isnull=False)
                    for detalle in detalles_fijos:
                        inv = InventarioSucursal.objects.filter(sucursal=pedido.sucursal, variante=detalle.variante).first()
                        if not inv or inv.stock < (detalle.cantidad * item.cantidad):
                            raise ValidationError({'error': f'Stock insuficiente para item de promo: {detalle.variante.producto.nombre}'})
                
                # 3. Verificar las opciones elegidas (esto vale para ambos: extras, salsas, pizzas elegidas en promo)
                for opcion in item.opciones_promocion.all():
                    inv_opc = InventarioSucursal.objects.filter(sucursal=pedido.sucursal, variante=opcion.variante).first()
                    if not inv_opc or inv_opc.stock < (opcion.cantidad * item.cantidad):
                        raise ValidationError({'error': f'Stock insuficiente para extra/opción: {opcion.variante.producto.nombre}'})

            # Crear PedidoItems (esto ejecutará PedidoItem.save() que descuenta el stock)
            for item in items:
                # Determinar precio base
                precio_base = item.variante.precio if item.variante else item.promocion.precio
                
                pedido_item = PedidoItem.objects.create(
                    pedido=pedido,
                    variante=item.variante,
                    promocion=item.promocion,
                    cantidad=item.cantidad,
                    precio=precio_base
                )
                
                # Copiar opciones del carrito al pedido (para que el historial sea fiel y el precio suba)
                for opcion in item.opciones_promocion.all():
                    PedidoItemOpcion.objects.create(
                        pedido_item=pedido_item,
                        variante=opcion.variante,
                        cantidad=opcion.cantidad
                    )
        
            # Limpiar carrito
            items.delete()
            # carrito.delete() # Opcional si quieres borrar el carrito entero o solo vaciarlo

class PedidoItemListCreate(generics.ListCreateAPIView):
    queryset = PedidoItem.objects.all()
    serializer_class = PedidoItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Filtrar por pedido si se especifica
        pedido_id = self.request.query_params.get('pedido_id')
        if pedido_id:
            return PedidoItem.objects.filter(pedido_id=pedido_id)
        return PedidoItem.objects.all()


# === PAGOS ===
class PagoListCreate(ListCreateView):
    serializer_class = PagoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Filtrar por pedido si se especifica
        pedido_id = self.request.query_params.get('pedido_id')
        if pedido_id:
            return Pago.objects.filter(pedido_id=pedido_id)
        return Pago.objects.all()


# ====================================================
# 🔄 AUTENTICACIÓN Y TOKENS
# ====================================================

class Status(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        # Detectar si es un UsuarioAdmin o si es un Cliente
        # Dependiendo de cómo esté configurado SimpleJWT, request.user puede ser un UsuarioAdmin 
        # con el ID del cliente, o el cliente mismo si se configuró así.
        
        # Por ahora, devolvemos la info básica que tenemos
        # Si es un objeto Cliente (o se comporta como tal)
        if hasattr(user, 'usuario') and hasattr(user, 'correo'):
            return Response({
                "usuario": user.usuario,
                "correo": getattr(user, 'correo', ''),
                "telefono": getattr(user, 'telefono', ''),
                "id_cliente": getattr(user, 'id_cliente', None),
                "is_authenticated": True,
            }, status=status.HTTP_200_OK)
        
        return Response({"detail": "Authenticated"}, status=status.HTTP_200_OK)


class RegistroView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = ClienteSerializer(data=request.data.copy())
        if serializer.is_valid():
            cliente = serializer.save()
            tokens = get_tokens_for_user(cliente)

            response = Response({"detail": "Usuario registrado exitosamente"}, status=status.HTTP_201_CREATED)

            response.set_cookie(
                key='access_token',
                value=tokens['access'],
                httponly=True,
                secure=False,
                max_age=60 * 60 * 24, # 1 día
                samesite='Lax',
                path='/'
            )
            response.set_cookie(
                key='refresh_token',
                value=tokens['refresh'],
                httponly=True,
                secure=False,
                max_age=60 * 60 * 24 * 7, # 7 días
                samesite='Lax',
                path='/'
            )
            return response

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        usuario_input = request.data.get('usuario')
        contrasena = request.data.get('contrasena')

        # Try searching by username first, then by email
        cliente = Cliente.objects.filter(usuario=usuario_input).first()
        if not cliente:
            cliente = Cliente.objects.filter(correo=usuario_input).first()
        
        if not cliente:
            return Response({'detail': f'Usuario/Email {usuario_input} no encontrado'}, status=status.HTTP_404_NOT_FOUND)

        if check_password(contrasena, cliente.contrasena):
            refresh = RefreshToken.for_user(cliente)
            access = refresh.access_token

            # Preparamos los datos del cliente para enviarlos
            cliente_data = {
                'id_cliente': cliente.id_cliente,
                'usuario': cliente.usuario,
                'correo': cliente.correo,
                'telefono': cliente.telefono,
            }

            response = Response({
                'detail': 'Inicio de sesión exitoso',
                'user': cliente_data
            }, status=status.HTTP_200_OK)
            response.set_cookie(
                key='access_token',
                value=str(access),
                httponly=True,
                secure=False,
                max_age=60 * 60 * 24, # 1 día
                samesite='Lax',
                path='/', # Crucial para que el resto de la API lo vea
            )
            response.set_cookie(
                key='refresh_token',
                value=str(refresh),
                httponly=True,
                secure=False,
                max_age=60 * 60 * 24 * 7, # 7 días
                samesite='Lax',
                path='/', # Crucial
            )
            return response
        else:
            return Response({'detail': 'Credenciales incorrectas'}, status=status.HTTP_401_UNAUTHORIZED)


class RefreshTokenView(TokenRefreshView):
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get('refresh_token')
        if refresh_token:
            request.data['refresh'] = refresh_token
            response = super().post(request, *args, **kwargs)

            if response.status_code == 200:
                new_access_token = response.data.get('access', None)
                if new_access_token:
                    response.delete_cookie('access_token', path='/')
                    response.set_cookie(
                        key='access_token',
                        value=new_access_token,
                        httponly=True,
                        secure=False,
                        max_age=60 * 60 * 24, # 1 día
                        samesite='Lax',
                        path='/'
                    )
                    response.data = {'message': 'Access Token refreshed successfully'}
                else:
                    response.data = {'detail': 'New tokens not found in response'}
                    response.status_code = status.HTTP_400_BAD_REQUEST
            return response
        else:
            return Response({"detail": "Refresh token not found"}, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        response = Response({"detail": "Sesión cerrada"}, status=status.HTTP_200_OK)
        # Limpiar cookies en el path raíz
        response.delete_cookie('access_token', path='/')
        response.delete_cookie('refresh_token', path='/')
        return response
    def post(self, request):
        return self.get(request)


# ====================================================
# 🔍 BÚSQUEDAS DINÁMICAS
# ====================================================

class DynamicSearchView(generics.GenericAPIView):
    def get(self, request, columna, valor_a_buscar):
        model_name = self.get_model_name()

        try:
            model = apps.get_model('api', model_name)
        except LookupError:
            return Response({"error": "Modelo no encontrado."}, status=400)

        if not hasattr(model, columna):
            return Response({"error": "Columna no válida."}, status=400)

        queryset = model.objects.filter(**{columna: valor_a_buscar})
        if not queryset.exists():
            return Response({"error": f"{model_name} no encontrado/a con ese valor en {columna}."}, status=404)

        serializer_class = self.get_serializer_class(model_name)
        serializer = serializer_class(queryset, many=True)
        return Response(serializer.data)

    def get_serializer_class(self, model_name):
        mapping = {
            'UsuarioAdmin': UsuarioAdminSerializer,
            'Cliente': ClienteSerializer,
            'Categoria': CategoriaSerializer,
            'Producto': ProductoSerializer,
            'ProductoVariante': ProductoVarianteSerializer,
            'Sucursal': SucursalSerializer,
            'Empleado': EmpleadoSerializer,
            'Historial': HistorialSerializer,
            'Promocion': PromocionSerializer,
            'PromocionDetalle': PromocionDetalleSerializer,
            'Carrito': CarritoSerializer,
            'CarritoItem': CarritoItemSerializer,
            'Pedido': PedidoSerializer,
            'PedidoItem': PedidoItemSerializer,
            'InventarioSucursal': InventarioSucursalSerializer,
            'Pago': PagoSerializer,
        }
        if model_name not in mapping:
            raise LookupError("Serializador sin definir para este modelo.")
        return mapping[model_name]

    def get_model_name(self):
        raise NotImplementedError("Este método debe ser implementado en las subclases.")


# ====================================================
# 🔎 VISTAS DE BÚSQUEDA ESPECÍFICAS - NUEVA ESTRUCTURA
# ====================================================

class UsuarioAdminSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'UsuarioAdmin'

class ClienteSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'Cliente'

class CategoriaSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'Categoria'

class ProductoSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'Producto'

class ProductoVarianteSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'ProductoVariante'

class SucursalSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'Sucursal'

class EmpleadoSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'Empleado'

class HistorialSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'Historial'

class PromocionSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'Promocion'

class PromocionDetalleSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'PromocionDetalle'

class CarritoSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'Carrito'

class CarritoItemSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'CarritoItem'

class PedidoSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'Pedido'

class PedidoItemSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'PedidoItem'

class InventarioSucursalSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'InventarioSucursal'

class PagoSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'Pago'