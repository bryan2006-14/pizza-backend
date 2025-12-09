from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import *
from rest_framework.exceptions import NotFound
from django.apps import apps

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
# 📋 CRUD PRINCIPALES
# ====================================================

class AreaListCreate(ListCreateView):
    serializer_class = AreaSerializer


class CategoriaListCreate(ListCreateView):
    serializer_class = CategoriaSerializer


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


class SucursalListCreate(ListCreateView):
    serializer_class = SucursalSerializer


class PagoListCreate(ListCreateView):
    serializer_class = PagoSerializer


class PedidoListCreate(ListCreateView):
    serializer_class = PedidoSerializer


class ProductoVentaListCreate(ListCreateView):
    serializer_class = ProductoVentaSerializer

    def put(self, request, *args, **kwargs):
        id_proventa = request.data.get('id_proventa', None)
        if not id_proventa:
            return Response({"detail": "id_proventa is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            producto = ProductoVenta.objects.get(id_proventa=id_proventa)
        except ProductoVenta.DoesNotExist:
            return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(producto, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        id_proventa = request.data.get('id_proventa', None)
        if not id_proventa:
            return Response({"detail": "id_proventa is required."}, status=status.HTTP_400_BAD_REQUEST)

        productos = ProductoVenta.objects.filter(id_proventa=id_proventa)
        if productos.exists():
            productos.delete()
            return Response({"detail": "Producto eliminado exitosamente."}, status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"detail": "No hay productos existentes con el id_proventa proporcionado"}, status=status.HTTP_404_NOT_FOUND)


class ProductoPrimaListCreate(generics.ListCreateAPIView):
    queryset = ProductoPrima.objects.all().order_by('id_proprima')  # ✅ campo correcto
    serializer_class = ProductoPrimaSerializer


class DetallePedidoListCreate(ListCreateView):
    serializer_class = DetallePedidoSerializer


class PaqueteListCreate(ListCreateView):
    serializer_class = PaqueteSerializer

    def delete(self, request, *args, **kwargs):
        id_proventa = request.data.get('id_proventa', None)
        if not id_proventa:
            return Response({"detail": "id_proventa is required."}, status=status.HTTP_400_BAD_REQUEST)

        paquetes = Paquete.objects.filter(id_proventa=id_proventa)
        if paquetes.exists():
            paquetes.delete()
            return Response({"detail": "Paquete eliminado exitosamente."}, status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"detail": "No hay paquetes existentes con el id_proventa proporcionado."}, status=status.HTTP_404_NOT_FOUND)


class EmpleadoListCreate(ListCreateView):
    serializer_class = EmpleadoSerializer


class HistorialListCreate(ListCreateView):
    serializer_class = HistorialSerializer


class TipoRepertorioListCreate(ListCreateView):
    serializer_class = TipoRepertorioSerializer


class RepertorioListCreate(ListCreateView):
    serializer_class = RepertorioSerializer


class DetalleRepertorioListCreate(ListCreateView):
    serializer_class = DetalleRepertorioSerializer


class CarritoListCreate(ListCreateView):
    serializer_class = CarritoSerializer

    def delete(self, request, *args, **kwargs):
        proventa_id = request.data.get('id_proventa', None)
        if proventa_id:
            try:
                carrito = Carrito.objects.get(id_proventa=proventa_id)
                carrito.delete()
                return Response({"message": "Producto quitado del carrito con éxito."}, status=status.HTTP_204_NO_CONTENT)
            except Carrito.DoesNotExist:
                return Response({"error": "Producto no encontrado en el carrito."}, status=status.HTTP_404_NOT_FOUND)
        else:
            return Response({"error": "No se proporcionó un id_proventa."}, status=status.HTTP_400_BAD_REQUEST)


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
            'Area': AreaSerializer,
            'Cliente': ClienteSerializer,
            'Categoria': CategoriaSerializer,
            'Sucursal': SucursalSerializer,
            'Pedido': PedidoSerializer,
            'Pago': PagoSerializer,
            'TipoRepertorio': TipoRepertorioSerializer,
            'Repertorio': RepertorioSerializer,
            'DetalleRepertorio': DetalleRepertorioSerializer,
            'ProductoVenta': ProductoVentaSerializer,
            'ProductoPrima': ProductoPrimaSerializer,
            'DetallePedido': DetallePedidoSerializer,
            'Paquete': PaqueteSerializer,
            'Empleado': EmpleadoSerializer,
            'Historial': HistorialSerializer,
            'Carrito': CarritoSerializer,
        }
        if model_name not in mapping:
            raise LookupError("Serializador sin definir para este modelo.")
        return mapping[model_name]

    def get_model_name(self):
        raise NotImplementedError("Este método debe ser implementado en las subclases.")


# ====================================================
# 🔎 VISTAS DE BÚSQUEDA ESPECÍFICAS
# ====================================================

class AreaSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'Area'


class ClienteSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'Cliente'


class CategoriaSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'Categoria'


class SucursalSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'Sucursal'


class PedidoSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'Pedido'


class PagoSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'Pago'


class TipoRepertorioSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'TipoRepertorio'


class RepertorioSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'Repertorio'


class DetalleRepertorioSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'DetalleRepertorio'


class ProductoVentaSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'ProductoVenta'


class ProductoPrimaSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'ProductoPrima'


class DetallePedidoSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'DetallePedido'


class PaqueteSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'Paquete'


class EmpleadoSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'Empleado'


class HistorialSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'Historial'


class CarritoSearchView(DynamicSearchView):
    def get_model_name(self):
        return 'Carrito'
