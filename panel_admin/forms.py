from django import forms
from api.models import *
from django.contrib.auth.hashers import make_password

class BaseForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control col-md-6'

class AreaForm(BaseForm):
    class Meta:
        model = Area
        fields = ['nombre_area', 'descripcion']

class CategoriaForm(BaseForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion']

class SucursalForm(BaseForm):
    class Meta:
        model = Sucursal
        fields = ['telefono', 'direccion', 'hora_inicio', 'hora_cierre']
        widgets = {
            'hora_inicio': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control col-6'}),
            'hora_cierre': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control col-6'}),
        }

class EmpleadoForm(BaseForm):
    class Meta:
        model = Empleado
        fields = ['id_sucursal', 'id_area', 'nombre', 'apellido', 'cargo', 'estado']

class ProductoVentaForm(BaseForm):
    class Meta:
        model = ProductoVenta
        fields = ['id_repertorio', 'estado', 'codigo']

class RepertorioForm(BaseForm):
    class Meta:
        model = Repertorio
        fields = ['titulo', 'descripcion', 'precio', 'fecha_inic', 'fecha_fin', 'tipo_repertorio', 'imagen', 'servidor']
        widgets = {
            'fecha_inic': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),
            'fecha_fin': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
            }),
            'imagen': forms.FileInput(attrs={
                'class': 'form-control-file col-md-6',
                'accept': '.png, .jpg, .jpeg'
            }),
        }


class ProductoPrimaForm(BaseForm):
    class Meta:
        model = ProductoPrima
        fields = ['id_categoria', 'nombre', 'precio', 'tamano', 'stock']


class PaqueteForm(BaseForm):
    class Meta:
        model = Paquete
        fields = ['id_proventa', 'id_proprima', 'cantidad']

class PedidoForm(BaseForm):
    class Meta:
        model = Pedido
        fields = ['id_sucursal', 'id_cliente', 'fecha_pedido', 'fecha_entrega', 'estado', 'codigo', 'direccion']
        widgets = {
            'fecha_pedido': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control',
            }),
            'fecha_entrega': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control',
            }),
        }

class DetallePedidoForm(BaseForm):
    class Meta:
        model = DetallePedido
        fields = ['id_pedido', 'id_proventa', 'precio']

class PagoForm(BaseForm):
    class Meta:
        model = Pago
        fields = ['id_pedido', 'monto', 'metodo_pago', 'estado']

class HistorialForm(BaseForm):
    class Meta:
        model = Historial
        fields = ['id_empleado', 'id_pedido', 'detalle', 'fecha']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
        }

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

class DetalleRepertorioForm(BaseForm):
    class Meta:
        model = DetalleRepertorio
        fields = ['id_repertorio', 'id_proprima', 'producto', 'unidades', 'detalle']

class CarritoForm(BaseForm):
    class Meta:
        model = Carrito
        fields = ['id_cliente', 'id_proventa']