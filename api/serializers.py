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
    
    class Meta:
        model = PromocionDetalle
        fields = '__all__'

class PromocionSerializer(serializers.ModelSerializer):
    detalles = PromocionDetalleSerializer(many=True, read_only=True)
    
    class Meta:
        model = Promocion
        fields = '__all__'

# ==================== CARRITO ====================

class CarritoItemSerializer(serializers.ModelSerializer):
    variante_info = ProductoVarianteSerializer(source='variante', read_only=True)
    promocion_info = PromocionSerializer(source='promocion', read_only=True)
    subtotal = serializers.SerializerMethodField()
    
    class Meta:
        model = CarritoItem
        fields = '__all__'
    
    def get_subtotal(self, obj):
        if obj.variante:
            return float(obj.variante.precio) * obj.cantidad
        elif obj.promocion:
            return float(obj.promocion.precio) * obj.cantidad
        return 0
    
    def validate(self, data):
        # Validar que solo uno de los dos (variante o promocion) esté presente
        if data.get('variante') and data.get('promocion'):
            raise serializers.ValidationError("No puedes tener variante y promoción en el mismo item")
        if not data.get('variante') and not data.get('promocion'):
            raise serializers.ValidationError("Debes especificar una variante o una promoción")
        return data

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
            if item.variante:
                total += float(item.variante.precio) * item.cantidad
            elif item.promocion:
                total += float(item.promocion.precio) * item.cantidad
        return total

# ==================== PEDIDOS ====================

class PedidoItemSerializer(serializers.ModelSerializer):
    variante_info = ProductoVarianteSerializer(source='variante', read_only=True)
    promocion_info = PromocionSerializer(source='promocion', read_only=True)
    subtotal = serializers.SerializerMethodField()
    
    class Meta:
        model = PedidoItem
        fields = '__all__'
    
    def get_subtotal(self, obj):
        return float(obj.precio) * obj.cantidad
    
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
        total = sum(float(item.precio) * item.cantidad for item in obj.items.all())
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