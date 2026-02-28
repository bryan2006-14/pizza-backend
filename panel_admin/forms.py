from django import forms
from api.models import *
from django.contrib.auth.hashers import make_password

class BaseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control col-md-6'

# ==================== USUARIOS ====================

class ClienteForm(BaseForm):
    class Meta:
        model = Cliente
        fields = ['usuario', 'correo', 'telefono', 'contrasena']
        widgets = {
            'contrasena': forms.PasswordInput(attrs={'class': 'form-control'}),
        }
    
    def save(self, commit=True):
        cliente = super().save(commit=False)
        cliente.contrasena = make_password(self.cleaned_data['contrasena'])
        if commit:
            cliente.save()
        return cliente

class UsuarioAdminForm(BaseForm):
    class Meta:
        model = UsuarioAdmin
        fields = ['usuario', 'rol', 'password']
        widgets = {
            'password': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data['password']:
            user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user

# ==================== NEGOCIO - PRODUCTOS ====================

class CategoriaForm(BaseForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion']

class ProductoForm(BaseForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'descripcion', 'categoria', 'imagen']
        widgets = {
            'imagen': forms.FileInput(attrs={
                'class': 'form-control-file col-md-6',
                'accept': '.png, .jpg, .jpeg'
            }),
        }

class ProductoVarianteForm(BaseForm):
    class Meta:
        model = ProductoVariante
        fields = ['producto', 'tamaño', 'precio']

# ==================== NEGOCIO - SUCURSALES Y EMPLEADOS ====================

class SucursalForm(BaseForm):
    class Meta:
        model = Sucursal
        fields = ['telefono', 'direccion', 'hora_inicio', 'hora_cierre']
        widgets = {
            'hora_inicio': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control col-6'}),
            'hora_cierre': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control col-6'}),
        }

class InventarioSucursalForm(BaseForm):
    class Meta:
        model = InventarioSucursal
        fields = ['sucursal', 'variante', 'stock']

class EmpleadoForm(BaseForm):
    class Meta:
        model = Empleado
        fields = ['sucursal', 'nombre', 'apellido', 'cargo', 'estado']

class HistorialForm(BaseForm):
    class Meta:
        model = Historial
        fields = ['empleado', 'pedido', 'detalle', 'fecha']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
        }

# ==================== PROMOCIONES ====================

class PromocionForm(BaseForm):
    class Meta:
        model = Promocion
        fields = ['titulo', 'descripcion', 'precio', 'imagen']
        widgets = {
            'imagen': forms.FileInput(attrs={
                'class': 'form-control-file col-md-6',
                'accept': '.png, .jpg, .jpeg'
            }),
        }

class PromocionDetalleForm(BaseForm):
    class Meta:
        model = PromocionDetalle
        fields = ['promocion', 'variante', 'cantidad']

# ==================== CARRITO ====================

class CarritoForm(BaseForm):
    class Meta:
        model = Carrito
        fields = ['cliente']

class CarritoItemForm(BaseForm):
    class Meta:
        model = CarritoItem
        fields = ['carrito', 'variante', 'promocion', 'cantidad']

# ==================== PEDIDOS ====================

class PedidoForm(BaseForm):
    class Meta:
        model = Pedido
        fields = ['cliente', 'sucursal', 'fecha_entrega', 'estado', 'codigo', 'direccion']
        widgets = {
            'fecha_entrega': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control',
            }),
        }

class PedidoItemForm(BaseForm):
    class Meta:
        model = PedidoItem
        fields = ['pedido', 'variante', 'promocion', 'cantidad', 'precio']

# ==================== PAGOS ====================

class PagoForm(BaseForm):
    class Meta:
        model = Pago
        fields = ['pedido', 'monto', 'metodo_pago', 'estado']