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
        variante = serializer.validated_data.get('variante')
        cantidad = serializer.validated_data.get('cantidad', 1)
        
        if variante and variante.stock < cantidad:
            raise ValidationError({
                'error': f'Stock insuficiente. Solo hay {variante.stock} unidades disponibles.'
            })
        
        serializer.save()


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
        pedido = serializer.save()
        carrito = Carrito.objects.filter(cliente=pedido.cliente, activo=True).first()

        if carrito:
            items = CarritoItem.objects.filter(carrito=carrito)
        
            # Verificar stock de todos los items
            for item in items:
                if item.variante and item.variante.stock < item.cantidad:
                    raise ValidationError(f'Stock insuficiente para {item.variante.producto.nombre} - {item.variante.tamaño}')
            
                elif item.promocion:
                    detalles = PromocionDetalle.objects.filter(promocion=item.promocion)
                    for detalle in detalles:
                        if detalle.variante.stock < (detalle.cantidad * item.cantidad):
                            raise ValidationError(f'Stock insuficiente para promoción {item.promocion.titulo}')
        
            # Procesar items y descontar stock
            for item in items:
                if item.variante:
                    # Crear PedidoItem para producto
                    PedidoItem.objects.create(
                        pedido=pedido,
                        variante=item.variante,
                        cantidad=item.cantidad,
                        precio=item.variante.precio
                    )
                    # Descontar stock
                    item.variante.stock -= item.cantidad
                    item.variante.save()
            
                elif item.promocion:
                    # Crear PedidoItem para promoción
                    PedidoItem.objects.create(
                        pedido=pedido,
                        promocion=item.promocion,
                        cantidad=item.cantidad,
                        precio=item.promocion.precio
                    )
                    
                    # Descontar stock de cada detalle de la promoción
                    detalles = PromocionDetalle.objects.filter(promocion=item.promocion)
                    for detalle in detalles:
                        cantidad_total = detalle.cantidad * item.cantidad
                        detalle.variante.stock -= cantidad_total
                        detalle.variante.save()
        
            # Vaciar carrito
            items.delete()
            carrito.delete()

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
    permission_classes = [AllowAny]
    def get(self, request):
        return Response({"detail": "success"}, status=status.HTTP_200_OK)


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
                max_age=60 * 5,
                samesite='Lax'
            )
            response.set_cookie(
                key='refresh_token',
                value=tokens['refresh'],
                httponly=True,
                secure=False,
                max_age=60 * 60 * 24 * 7,
                samesite='Lax'
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

            response = Response({'detail': 'Inicio de sesión exitoso'}, status=status.HTTP_200_OK)
            response.set_cookie(
                key='access_token',
                value=str(access),
                httponly=True,
                secure=False,
                max_age=60 * 4,
                samesite='Lax',
            )
            response.set_cookie(
                key='refresh_token',
                value=str(refresh),
                httponly=True,
                secure=False,
                max_age=60 * 60 * 24 * 7,
                samesite='Lax',
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
                    response.delete_cookie('access_token')
                    response.set_cookie(
                        key='access_token',
                        value=new_access_token,
                        httponly=True,
                        secure=False,
                        max_age=60 * 4,
                        samesite='Lax'
                    )
                    response.data = {'message': 'Access Token refreshed successfully'}
                else:
                    response.data = {'detail': 'New tokens not found in response'}
                    response.status_code = status.HTTP_400_BAD_REQUEST
            return response
        else:
            return Response({"detail": "Refresh token not found"}, status=status.HTTP_400_BAD_REQUEST)


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

class PagoSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'Pago'