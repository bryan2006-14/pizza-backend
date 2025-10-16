from rest_framework import serializers
from .models import *
from django.contrib.auth.hashers import make_password

class RestablecerContrasenaSerializer(serializers.Serializer):
    contrasena = serializers.CharField(write_only=True)

class AreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = '__all__'

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = '__all__'

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

class SucursalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sucursal
        fields = '__all__'

class PagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pago
        fields = '__all__'

class PedidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pedido
        fields = '__all__'

class ProductoVentaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductoVenta
        fields = '__all__'

class ProductoPrimaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductoPrima
        fields = '__all__'

class DetallePedidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetallePedido
        fields = '__all__'

class PaqueteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paquete
        fields = '__all__'

class EmpleadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empleado
        fields = '__all__'

class HistorialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Historial
        fields = '__all__'

class RepertorioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Repertorio
        fields = '__all__'

class DetalleRepertorioSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleRepertorio
        fields = '__all__'

class CarritoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Carrito
        fields = '__all__'