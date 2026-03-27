from rest_framework import serializers
from .models import *
from django.contrib.auth.hashers import make_password

# ==================== USUARIOS ====================

class RestablecerContrasenaSerializer(serializers.Serializer):
    contrasena = serializers.CharField(write_only=True)

class UsuarioAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsuarioAdmin
        fields = ['id', 'usuario', 'rol', 'is_staff', 'is_active']
        read_only_fields = ['id']

class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = '__all__'
    
    def create(self, validated_data):
        validated_data['contrasena'] = make_password(validated_data['contrasena'])
        return super(ClienteSerializer, self).create(validated_data)

    def update(self, instance, validated_data):
        if 'contrasena' in validated_data:
            validated_data['contrasena'] = make_password(validated_data['contrasena'])
        return super(ClienteSerializer, self).update(instance, validated_data)

# ==================== NEGOCIO - PRODUCTOS ====================

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'

class ProductoVarianteSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_imagen = serializers.CharField(source='producto.imagen', read_only=True)
    producto_descripcion = serializers.CharField(source='producto.descripcion', read_only=True)
    
    class Meta:
        model = ProductoVariante
        fields = '__all__'

class ProductoSerializer(serializers.ModelSerializer):
    variantes = ProductoVarianteSerializer(many=True, read_only=True)
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    
    class Meta:
        model = Producto
        fields = '__all__'

# ==================== NEGOCIO - SUCURSALES Y EMPLEADOS ====================

class SucursalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sucursal
        fields = '__all__'

class InventarioSucursalSerializer(serializers.ModelSerializer):
    sucursal_direccion = serializers.CharField(source='sucursal.direccion', read_only=True)
    producto_nombre = serializers.CharField(source='variante.producto.nombre', read_only=True)
    variante_tamano = serializers.CharField(source='variante.tamaño', read_only=True)

    class Meta:
        model = InventarioSucursal
        fields = '__all__'

class EmpleadoSerializer(serializers.ModelSerializer):
    sucursal_direccion = serializers.CharField(source='sucursal.direccion', read_only=True)
    
    class Meta:
        model = Empleado
        fields = '__all__'

class HistorialSerializer(serializers.ModelSerializer):
    empleado_nombre = serializers.SerializerMethodField()
    pedido_codigo = serializers.CharField(source='pedido.codigo', read_only=True)
    
    class Meta:
        model = Historial
        fields = '__all__'
    
    def get_empleado_nombre(self, obj):
        return f"{obj.empleado.nombre} {obj.empleado.apellido}"

# ==================== PROMOCIONES ====================

class PromocionDetalleSerializer(serializers.ModelSerializer):
    variante_info = ProductoVarianteSerializer(source='variante', read_only=True)
    categoria_info = CategoriaSerializer(source='categoria', read_only=True)
    
    class Meta:
        model = PromocionDetalle
        fields = '__all__'

class PromocionSerializer(serializers.ModelSerializer):
    detalles = PromocionDetalleSerializer(many=True, read_only=True)
    
    class Meta:
        model = Promocion
        fields = '__all__'

# ==================== CARRITO ====================

class CarritoItemOpcionSerializer(serializers.ModelSerializer):
    variante_info = ProductoVarianteSerializer(source='variante', read_only=True)
    
    class Meta:
        model = CarritoItemOpcion
        fields = '__all__'
        read_only_fields = ['carrito_item']

class CarritoItemSerializer(serializers.ModelSerializer):
    variante_info = ProductoVarianteSerializer(source='variante', read_only=True)
    promocion_info = PromocionSerializer(source='promocion', read_only=True)
    opciones_promocion = CarritoItemOpcionSerializer(many=True, required=False)
    subtotal = serializers.SerializerMethodField()
    
    class Meta:
        model = CarritoItem
        fields = '__all__'
    
    def get_subtotal(self, obj):
        price = 0
        if obj.variante:
            price = float(obj.variante.precio)
        elif obj.promocion:
            price = float(obj.promocion.precio)
        
        # Sumar el precio de las opciones (extras, salsas, etc.)
        for opcion in obj.opciones_promocion.all():
            # Si el item principal es un producto simple, cualquier opción es un extra de pago
            if obj.variante:
                price += float(opcion.variante.precio) * opcion.cantidad
            else:
                # Si es una promoción, solo sumamos el precio si NO es una pizza o bebida 
                # (suponiendo que las pizzas/bebidas ya están incluidas en el precio del combo)
                cat = (opcion.variante.producto.categoria.nombre if opcion.variante.producto.categoria else "").lower()
                if 'pizza' not in cat and 'bebida' not in cat and 'gaseosa' not in cat:
                    price += float(opcion.variante.precio) * opcion.cantidad
            
        return price * obj.cantidad
    
    def validate(self, data):
        # Para validación, necesitamos saber qué hay ya en el objeto si es una actualización
        instance = getattr(self, 'instance', None)
        
        # Obtenemos los valores actuales (del request o de la instancia)
        variante = data.get('variante') if 'variante' in data else (instance.variante if instance else None)
        promocion = data.get('promocion') if 'promocion' in data else (instance.promocion if instance else None)

        if variante and promocion:
            raise serializers.ValidationError("No puedes tener variante y promoción en el mismo item")
        if not variante and not promocion:
            raise serializers.ValidationError("Debes especificar una variante o una promoción")
        return data

    def create(self, validated_data):
        opciones_data = validated_data.pop('opciones_promocion', [])
        carrito_item = super().create(validated_data)
        for opcion in opciones_data:
            CarritoItemOpcion.objects.create(carrito_item=carrito_item, **opcion)
        return carrito_item

class CarritoSerializer(serializers.ModelSerializer):
    items = CarritoItemSerializer(many=True, read_only=True)
    cliente_nombre = serializers.CharField(source='cliente.usuario', read_only=True)
    total = serializers.SerializerMethodField()
    
    class Meta:
        model = Carrito
        fields = '__all__'
    
    def get_total(self, obj):
        total = 0
        for item in obj.items.all():
            # Usar el método get_subtotal que ya definimos arriba
            total += CarritoItemSerializer().get_subtotal(item)
        return total

# ==================== PEDIDOS ====================

class PedidoItemOpcionSerializer(serializers.ModelSerializer):
    variante_info = ProductoVarianteSerializer(source='variante', read_only=True)
    
    class Meta:
        model = PedidoItemOpcion
        fields = '__all__'

class PedidoItemSerializer(serializers.ModelSerializer):
    variante_info = ProductoVarianteSerializer(source='variante', read_only=True)
    promocion_info = PromocionSerializer(source='promocion', read_only=True)
    opciones_promocion = PedidoItemOpcionSerializer(many=True, read_only=True)
    subtotal = serializers.SerializerMethodField()
    
    class Meta:
        model = PedidoItem
        fields = '__all__'
    
    def get_subtotal(self, obj):
        price = float(obj.precio) # Este es el precio base guardado en el pedido
        
        # Sumar el precio de las opciones (extras, salsas, etc.) guardadas en este item
        for opcion in obj.opciones_promocion.all():
            # Si el item principal es un producto simple, cualquier opción es un extra de pago
            if obj.variante:
                price += float(opcion.variante.precio) * opcion.cantidad
            else:
                # Si es una promoción, solo sumamos el precio si NO es una pizza o bebida 
                # (suponiendo que las pizzas/bebidas ya están incluidas en el precio del combo)
                cat = (opcion.variante.producto.categoria.nombre if opcion.variante.producto.categoria else "").lower()
                if 'pizza' not in cat and 'bebida' not in cat and 'gaseosa' not in cat:
                    price += float(opcion.variante.precio) * opcion.cantidad
            
        return price * obj.cantidad
    
    def validate(self, data):
        # Validar que solo uno de los dos (variante o promocion) esté presente
        if data.get('variante') and data.get('promocion'):
            raise serializers.ValidationError("No puedes tener variante y promoción en el mismo item")
        if not data.get('variante') and not data.get('promocion'):
            raise serializers.ValidationError("Debes especificar una variante o una promoción")
        return data

class PedidoSerializer(serializers.ModelSerializer):
    items = PedidoItemSerializer(many=True, read_only=True)
    cliente_nombre = serializers.CharField(source='cliente.usuario', read_only=True)
    sucursal_direccion = serializers.CharField(source='sucursal.direccion', read_only=True)
    total = serializers.SerializerMethodField()
    pago_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Pedido
        fields = '__all__'
    
    def get_total(self, obj):
        total = 0
        for item in obj.items.all():
            item_price = float(item.precio)
            # Sumar extras/opciones igual que PedidoItemSerializer.get_subtotal
            for opcion in item.opciones_promocion.all():
                if item.variante:
                    item_price += float(opcion.variante.precio) * opcion.cantidad
                else:
                    cat = (opcion.variante.producto.categoria.nombre if opcion.variante.producto.categoria else "").lower()
                    if 'pizza' not in cat and 'bebida' not in cat and 'gaseosa' not in cat:
                        item_price += float(opcion.variante.precio) * opcion.cantidad
            total += item_price * item.cantidad
        # Sumar el costo de delivery si aplica
        total += float(obj.costo_delivery)
        return total
    
    def get_pago_info(self, obj):
        try:
            pago = obj.pago
            return {
                'id_pago': pago.id_pago,
                'monto': float(pago.monto),
                'metodo_pago': pago.metodo_pago,
                'estado': pago.estado
            }
        except:
            return None

# ==================== PAGOS ====================

class PagoSerializer(serializers.ModelSerializer):
    pedido_codigo = serializers.CharField(source='pedido.codigo', read_only=True)
    
    class Meta:
        model = Pago
        fields = '__all__'