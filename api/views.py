from rest_framework import generics
from .models import *
from .serializers import *

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import *
from rest_framework.exceptions import NotFound
from django.apps import apps

def get_tokens_for_user(cliente):
    refresh = RefreshToken.for_user(cliente)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class ListCreateView(generics.ListCreateAPIView):
    serializer_class = None
    queryset = None

    def get_queryset(self):
        model = self.serializer_class.Meta.model
        return model.objects.all()

class AreaListCreate(ListCreateView):
    serializer_class = AreaSerializer

class CategoriaListCreate(ListCreateView):
    serializer_class = CategoriaSerializer

class ClienteListCreateUpdate(generics.ListCreateAPIView):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer

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

class ProductoPrimaListCreate(ListCreateView):
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

# class EncryptPasswordView(APIView):
#     def post(self, request):
#         password = request.data.get("password")
#         if not password:
#             return Response({"error": "Password not provided"}, status=status.HTTP_400_BAD_REQUEST)
#         hashed_password = make_password(password)
#         return Response({"hashed_password": hashed_password}, status=status.HTTP_200_OK)

# class CheckPasswordView(APIView):
#     def post(self, request):
#         password = request.data.get("password")
#         hashed_password = request.data.get("hashed_password")

#         if not password or not hashed_password:
#             return Response({"error": "Password or hash not provided"}, status=status.HTTP_400_BAD_REQUEST)
#         password_is_correct = check_password(password, hashed_password)

#         if password_is_correct:
#             return Response({"message": "Password is correct"}, status=status.HTTP_200_OK)
#         else:
#             return Response({"message": "Password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)

class Status(APIView):
    def get(self, request):
        response = Response({"detail": "success"}, status=status.HTTP_200_OK)
        return response

class RegistroView(APIView):
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
                secure=True,
                max_age=60*5,
                samesite='Lax'
            )
            response.set_cookie(
                key='refresh_token',
                value=tokens['refresh'],
                httponly=True,
                secure=True,
                max_age=60*60*24*7,
                samesite='Lax'
            )

            return response

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    def post(self, request):
        usuario = request.data.get('usuario')
        contrasena = request.data.get('contrasena')

        try:
            cliente = Cliente.objects.get(usuario=usuario)
        except Cliente.DoesNotExist:
            return Response({'detail': 'Usuario no encontrado'}, status=status.HTTP_404_NOT_FOUND)

        if check_password(contrasena,cliente.contrasena):
            refresh = RefreshToken.for_user(cliente)
            access = refresh.access_token

            response = Response({'detail':'inicio de sesión exitoso'},status=status.HTTP_200_OK)

            response.set_cookie(
                key='access_token',
                value=str(access),
                httponly=True,
                secure=True,
                # max_age=60*60*1,
                max_age=60*4,
                samesite='Lax',
            )

            response.set_cookie(
                key='refresh_token',
                value=str(refresh),
                httponly=True,
                secure=True,
                max_age=60*60*24*7,
                samesite='Lax',
            )

            return response
        else:
            return Response({'detail': 'Credenciales incorrectas'}, status=status.HTTP_401_UNAUTHORIZED)

class RefreshTokenView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get('refresh_token')

        if refresh_token:
            request.data['refresh'] = refresh_token

            response = super().post(request, *args, **kwargs)

            if response.status_code == 200:
                new_access_token = response.data.get('access', None)
                # new_refresh_token = response.data.get('refresh', None)

                # print(new_refresh_token)
                if new_access_token:
                    response.delete_cookie('access_token')
                    # response.delete_cookie('refresh_token')

                    response.set_cookie(
                        key='access_token',
                        value=new_access_token,
                        httponly=True,
                        secure=True,
                        max_age=60*4,
                        samesite='Lax'
                    )

                    response.data = {'message': 'Access Token refreshed successfully'}
                else:
                    response.data = {'detail': 'New tokens not found in response'}
                    response.status_code = status.HTTP_400_BAD_REQUEST

            return response
        else:
            return Response({"detail": "Refresh token not found"}, status=status.HTTP_400_BAD_REQUEST)


class DynamicSearchView(generics.GenericAPIView):
    def get(self, request, columna, valor_a_buscar):
        model_name = self.get_model_name()

        try:
            model = apps.get_model('api', model_name)
        except LookupError:
            return Response({"error": "Modelo no encontrado."}, status=400)

        try:
            if hasattr(model, columna):
                queryset = model.objects.filter(**{columna: valor_a_buscar})
                if not queryset.exists():
                    return Response({"error": f"{model_name} no encontrado/a con ese valor en {columna}."}, status=404)

                serializer_class = self.get_serializer_class(model_name)
                serializer = serializer_class(queryset, many=True)
                return Response(serializer.data)
            else:
                return Response({"error": "Columna no válida."}, status=400)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    def get_serializer_class(self, model_name):
        if model_name == 'Area':
            return AreaSerializer
        elif model_name == 'Cliente':
            return ClienteSerializer
        elif model_name == 'Categoria':
            return CategoriaSerializer
        elif model_name == 'Sucursal':
            return SucursalSerializer
        elif model_name == 'Pedido':
            return PedidoSerializer
        elif model_name == 'Pago':
            return PagoSerializer
        elif model_name == 'Repertorio':
            return RepertorioSerializer
        elif model_name == 'DetalleRepertorio':
            return DetalleRepertorioSerializer
        elif model_name == 'ProductoVenta':
            return ProductoVentaSerializer
        elif model_name == 'ProductoPrima':
            return ProductoPrimaSerializer
        elif model_name == 'DetallePedido':
            return DetallePedidoSerializer
        elif model_name == 'Paquete':
            return PaqueteSerializer
        elif model_name == 'Empleado':
            return EmpleadoSerializer
        elif model_name == 'Historial':
            return HistorialSerializer
        elif model_name == 'Carrito':
            return CarritoSerializer
        else:
            raise LookupError("Serializador sin definir para este modelo.")

    def get_model_name(self):
        raise NotImplementedError("Este método debe ser implementado en las subclases.")

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