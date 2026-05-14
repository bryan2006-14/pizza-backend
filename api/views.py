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
import mercadopago
from django.conf import settings


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

class LimpiarCarritoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cliente_id = request.data.get('cliente_id') or getattr(request.user, 'id_cliente', None)
        if not cliente_id:
            return Response({"error": "ID de cliente no encontrado"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            Carrito.objects.filter(cliente_id=cliente_id).delete()
            return Response({"message": "Carrito limpiado exitosamente"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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

    def create(self, request, *args, **kwargs):
        # Log para depuración
        print(f"DEBUG: Datos recibidos para pedido: {request.data}")
        
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print(f"!!! ERROR VALIDACION SERIALIZADOR !!!: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except ValidationError as e:
            print(f"!!! ERROR VALIDACION PERFORM_CREATE !!!: {e.detail}")
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"!!! ERROR INESPERADO !!!:\n{error_trace}")
            return Response({
                "error": str(e),
                "traceback": error_trace
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get_queryset(self):
        # Filtrar por cliente si se especifica
        cliente_id = self.request.query_params.get('cliente_id')
        if cliente_id:
            return Pedido.objects.filter(cliente_id=cliente_id).order_by('-fecha_pedido')
        return Pedido.objects.all().order_by('-fecha_pedido')
        
    def perform_create(self, serializer):
        try:
            print("STEP 1: Guardando pedido base...")
            pedido = serializer.save()
            print(f"STEP 2: Pedido guardado con ID {pedido.id_pedido}")
            
            items_data = self.request.data.get('items', [])
            print(f"STEP 3: Procesando {len(items_data)} items enviados...")
            
            if not items_data:
                print("STEP 3.1: No hay items en request, buscando en Carrito DB...")
                carrito = Carrito.objects.filter(cliente=pedido.cliente).last()
                if carrito:
                    items_obj = CarritoItem.objects.filter(carrito=carrito)
                    for io in items_obj:
                        items_data.append({
                            'variante': io.variante.id_variante if io.variante else None,
                            'promocion': io.promocion.id_promocion if io.promocion else None,
                            'cantidad': io.cantidad,
                            'precio': io.variante.precio if io.variante else io.promocion.precio,
                            'opciones': [{'variante': op.variante.id_variante, 'cantidad': op.cantidad} for op in io.opciones_promocion.all()]
                        })
            
            from django.db import transaction
            with transaction.atomic():
                for i, item in enumerate(items_data):
                    v_id = item.get('variante')
                    p_id = item.get('promocion')
                    
                    # Limpieza: Si vienen como strings vacíos o "null", convertirlos a None real de Python
                    if not v_id or v_id == 'null': v_id = None
                    if not p_id or p_id == 'null': p_id = None
                    
                    # Validación de integridad antes de crear
                    if not v_id and not p_id:
                        print(f"ERROR: Item {i} no tiene ni variante ni promocion.")
                        continue # Saltamos items inválidos para evitar el error 500
                    
                    print(f"STEP 4.{i}: Creando PedidoItem (V:{v_id}, P:{p_id})...")
                    pedido_item = PedidoItem.objects.create(
                        pedido=pedido,
                        variante_id=v_id,
                        promocion_id=p_id,
                        cantidad=item.get('cantidad', 1),
                        precio=item.get('precio') or 0
                    )
                    
                    opciones = item.get('opciones', item.get('opciones_promocion', []))
                    for j, opc in enumerate(opciones):
                        print(f"STEP 4.{i}.{j}: Añadiendo opcion {opc.get('variante')}...")
                        PedidoItemOpcion.objects.create(
                            pedido_item=pedido_item,
                            variante_id=opc.get('variante'),
                            cantidad=opc.get('cantidad', 1)
                        )
            
            # print("STEP 5: Limpiando carrito de la base de datos...")
            # Carrito.objects.filter(cliente=pedido.cliente).delete()
            print("STEP 6: Proceso completado con éxito.")
            
        except Exception as e:
            print(f"!!! ERROR EN PERFORM_CREATE !!!: {str(e)}")
            import traceback
            traceback.print_exc()
            raise ValidationError({'error': f'Error interno al procesar el pedido: {str(e)}'})

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


# ====================================================
# 💳 MERCADO PAGO INTEGRATION
# ====================================================

@transaction.atomic
def procesar_pago_exitoso(payment_id, session_id):
    print(f"DEBUG: Iniciando procesar_pago_exitoso para MP_ID: {payment_id}, Session: {session_id}")
    
    # 1. Verificar si este pago ya fue procesado (idempotencia)
    pago_existente = Pago.objects.filter(mercado_pago_payment_id=str(payment_id)).first()
    if pago_existente:
        print(f"DEBUG: Pago {payment_id} ya existe. Retornando pedido existente.")
        return pago_existente.pedido

    # 2. Obtener la sesión con bloqueo para evitar procesamiento doble
    try:
        session = CheckoutSession.objects.select_for_update().get(id=session_id)
        print(f"DEBUG: Sesión encontrada para cliente: {session.cliente.usuario}")
        if session.pagado:
            print(f"DEBUG: Sesión {session_id} ya marcada como pagada.")
            return session.pedido_creado
    except CheckoutSession.DoesNotExist:
        print(f"ERROR: Sesión {session_id} no encontrada en la base de datos.")
        return None

    # 3. Crear el Pedido real
    try:
        # Calculamos el total de los items del snapshot
        total_items = 0
        for item in session.items_snapshot:
            subtotal = item.get('subtotal', 0)
            print(f"DEBUG: Item snapshot subtotal: {subtotal}")
            total_items += float(subtotal)
            
        total_final = total_items + float(session.costo_delivery)
        print(f"DEBUG: Total calculado: {total_final} (Items: {total_items} + Delivery: {session.costo_delivery})")

        pedido = Pedido.objects.create(
            cliente=session.cliente,
            sucursal=session.sucursal,
            direccion=session.direccion,
            tipo_entrega=session.tipo_entrega,
            costo_delivery=session.costo_delivery,
            estado='pendiente' # Se confirmará abajo
        )
        print(f"DEBUG: Pedido creado con ID: {pedido.id_pedido}, Codigo: {pedido.codigo}")

        # 4. Crear los PedidoItems desde el snapshot de la sesión
        for item_data in session.items_snapshot:
            # Obtener el precio unitario del item principal
            precio_unitario = 0
            if item_data.get('variante_info'):
                precio_unitario = float(item_data['variante_info'].get('precio', 0))
            elif item_data.get('promocion_info'):
                precio_unitario = float(item_data['promocion_info'].get('precio', 0))
            
            print(f"DEBUG: Creando PedidoItem para variante/promo. Precio: {precio_unitario}")
            
            pedido_item = PedidoItem.objects.create(
                pedido=pedido,
                variante_id=item_data.get('variante'),
                promocion_id=item_data.get('promocion'),
                cantidad=int(item_data.get('cantidad', 1)),
                precio=precio_unitario
            )
            
            # Copiar opciones/extras si existen
            opciones = item_data.get('opciones_promocion', [])
            for opcion_data in opciones:
                v_id = opcion_data.get('variante')
                cant = int(opcion_data.get('cantidad', 1))
                print(f"DEBUG: Añadiendo opción {v_id} x{cant}")
                PedidoItemOpcion.objects.create(
                    pedido_item=pedido_item,
                    variante_id=v_id,
                    cantidad=cant
                )

        # 5. Registrar el Pago
        pago = Pago.objects.create(
            pedido=pedido,
            monto=total_final,
            metodo_pago='tarjeta',
            estado='completado',
            mercado_pago_payment_id=payment_id,
            mercado_pago_preference_id=session.preference_id
        )
        print(f"DEBUG: Pago registrado: {pago.id_pago}")

        # 6. Descontar stock
        print("DEBUG: Ejecutando descuento de stock...")
        pedido.confirmar_y_descontar_stock()

        # 7. Marcar sesión como completada y vincular pedido
        session.pagado = True
        session.pedido_creado = pedido
        session.save()

        # 8. LIMPIAR EL CARRITO del cliente (borramos los items)
        from .models import CarritoItem
        deleted_count, _ = CarritoItem.objects.filter(carrito__cliente=session.cliente).delete()
        print(f"DEBUG: Carrito limpiado. Items borrados: {deleted_count}")

        return pedido

    except Exception as e:
        import traceback
        print(f"!!! ERROR CRITICO EN PROCESAR_PAGO_EXITOSO !!!: {str(e)}")
        print(traceback.format_exc())
        raise e

class MercadoPagoPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cliente_id = request.data.get('cliente') or getattr(request.user, 'id_cliente', None)
        sucursal_id = request.data.get('sucursal')
        direccion = request.data.get('direccion')
        tipo_entrega = request.data.get('tipo_entrega')
        costo_delivery = request.data.get('costo_delivery', 0)

        if not sucursal_id or not direccion:
            return Response({"error": "Faltan datos de sucursal o dirección"}, status=status.HTTP_400_BAD_REQUEST)

        # Obtener el carrito actual del cliente
        try:
            from .models import Carrito
            carrito = Carrito.objects.get(cliente_id=cliente_id)
        except Carrito.DoesNotExist:
            return Response({"error": "El carrito no existe"}, status=status.HTTP_404_NOT_FOUND)

        # Serializar el carrito para obtener el total y los items (snapshot)
        cart_serializer = CarritoSerializer(carrito)
        total_carrito = float(cart_serializer.data.get('total', 0))
        total_final = total_carrito + float(costo_delivery)

        if total_final <= 0:
            return Response({"error": "El carrito está vacío o el total es inválido"}, status=status.HTTP_400_BAD_REQUEST)

        # Configurar Mercado Pago
        sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)

        # Preparar la sesión de checkout (borrador)
        checkout_session = CheckoutSession.objects.create(
            cliente_id=cliente_id,
            sucursal_id=sucursal_id,
            direccion=direccion,
            tipo_entrega=tipo_entrega,
            costo_delivery=costo_delivery,
            preference_id=None, # Se actualizará después
            items_snapshot=cart_serializer.data['items'] # Guardamos qué está comprando
        )

        try:
            preference_data = {
                "items": [
                    {
                        "title": f"Pizza Total - Pedido en {tipo_entrega}",
                        "quantity": 1,
                        "unit_price": float(round(total_final, 2)),
                        "currency_id": "PEN"
                    }
                ],
                "external_reference": str(checkout_session.id),
                "back_urls": {
                    "success": "http://127.0.0.1:5173/pago-exitoso",
                    "failure": "http://127.0.0.1:5173/carrito",
                    "pending": "http://127.0.0.1:5173/pago-exitoso"
                },
                "auto_return": "approved",
                "payment_methods": {
                    "excluded_payment_types": [
                        {"id": "ticket"}
                    ],
                    "installments": 12
                },
            }
            
            print(f"DEBUG MP: Enviando data: {preference_data}")
            preference_response = sdk.preference().create(preference_data)
            
            if preference_response["status"] >= 400:
                error_detail = preference_response.get("response", "Sin detalle")
                print(f"!!! ERROR MP SDK !!! Status: {preference_response['status']}, Detail: {error_detail}")
                checkout_session.delete()
                return Response({
                    "error": "Error al crear la preferencia en Mercado Pago",
                    "detail": error_detail
                }, status=status.HTTP_400_BAD_REQUEST)

            preference = preference_response["response"]
            
            # Actualizar la sesión con el ID de preferencia real
            checkout_session.preference_id = preference['id']
            checkout_session.save()

            return Response({
                "preference_id": preference['id'],
                "init_point": preference['init_point']
            }, status=status.HTTP_200_OK)

        except Exception as e:
            if checkout_session.pk:
                checkout_session.delete()
            import traceback
            print(f"!!! EXCEPCION INTERNA !!!: {str(e)}")
            print(traceback.format_exc())
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MercadoPagoWebhookView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        resource_id = request.query_params.get('id') or request.data.get('data', {}).get('id')
        type_notif = request.data.get('type') or request.query_params.get('topic')

        if type_notif == 'payment' or type_notif == 'payment':
            try:
                sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
                payment_info = sdk.payment().get(resource_id)
                payment_data = payment_info["response"]

                status_mp = payment_data.get('status')
                session_id = payment_data.get('external_reference')

                if status_mp == 'approved' and session_id:
                    procesar_pago_exitoso(resource_id, session_id)
                    print(f"WEBHOOK: Pago {resource_id} procesado para sesión {session_id}")
                
            except Exception as e:
                print(f"WEBHOOK ERROR: {str(e)}")

        return Response(status=status.HTTP_200_OK)


class ConfirmarPagoManualView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        payment_id = request.data.get('payment_id')
        session_id = request.data.get('external_reference')
        print(f"DEBUG: Intento de confirmación manual. MP_ID: {payment_id}, Session: {session_id}")
        
        if not payment_id or not session_id:
            return Response({"error": "Faltan datos de confirmación"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Procesar el pago y crear el pedido si no existe
            pedido = procesar_pago_exitoso(payment_id, session_id)
            
            if pedido:
                return Response({
                    "message": "Pago confirmado y pedido creado exitosamente",
                    "id_pedido": pedido.id_pedido,
                    "codigo": pedido.codigo
                }, status=status.HTTP_200_OK)
            else:
                return Response({"error": "No se pudo procesar el pago o ya fue procesado."}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerificarCheckoutView(APIView):
    """
    Endpoint que el frontend llama al regresar de Mercado Pago.
    Busca la sesión de checkout por preference_id y verifica el pago via MP API.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        preference_id = request.data.get('preference_id')
        print(f"DEBUG VERIFICAR: Recibido preference_id: {preference_id}")
        
        if not preference_id:
            return Response({"error": "Falta preference_id"}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Buscar la sesión de checkout
        try:
            session = CheckoutSession.objects.get(preference_id=preference_id)
        except CheckoutSession.DoesNotExist:
            print(f"DEBUG VERIFICAR: Sesión no encontrada para preference: {preference_id}")
            return Response({"error": "Sesión de checkout no encontrada"}, status=status.HTTP_404_NOT_FOUND)

        # Si ya fue procesada, devolver el pedido existente
        if session.pagado and session.pedido_creado:
            print(f"DEBUG VERIFICAR: Sesión ya pagada. Pedido: {session.pedido_creado.id_pedido}")
            return Response({
                "status": "already_processed",
                "id_pedido": session.pedido_creado.id_pedido,
                "codigo": session.pedido_creado.codigo
            }, status=status.HTTP_200_OK)

        # 2. Consultar a Mercado Pago por los pagos de esta preferencia
        try:
            sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
            
            # Buscar pagos por external_reference (que es el session.id)
            search_result = sdk.payment().search({
                "external_reference": str(session.id)
            })
            
            print(f"DEBUG VERIFICAR: Respuesta búsqueda MP: status={search_result.get('status')}")
            
            if search_result.get("status") == 200:
                results = search_result.get("response", {}).get("results", [])
                print(f"DEBUG VERIFICAR: Pagos encontrados: {len(results)}")
                
                for payment in results:
                    payment_status = payment.get("status")
                    payment_id = str(payment.get("id"))
                    print(f"DEBUG VERIFICAR: Pago {payment_id} - Estado: {payment_status}")
                    
                    if payment_status == "approved":
                        # ¡Pago aprobado! Procesar el pedido
                        pedido = procesar_pago_exitoso(payment_id, str(session.id))
                        
                        if pedido:
                            return Response({
                                "status": "approved",
                                "id_pedido": pedido.id_pedido,
                                "codigo": pedido.codigo
                            }, status=status.HTTP_200_OK)
                
                # No hay pagos aprobados aún
                return Response({
                    "status": "pending",
                    "message": "No se encontraron pagos aprobados aún"
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "status": "error",
                    "message": "Error consultando Mercado Pago"
                }, status=status.HTTP_502_BAD_GATEWAY)

        except Exception as e:
            import traceback
            print(f"DEBUG VERIFICAR ERROR: {str(e)}")
            print(traceback.format_exc())
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)