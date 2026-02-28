from django.contrib import admin
from .models import (
    UsuarioAdmin, Cliente, Categoria, Producto, ProductoVariante,
    Sucursal, InventarioSucursal, Empleado, Historial, Promocion, PromocionDetalle,
    Carrito, CarritoItem, Pedido, PedidoItem, Pago
)

# ==================== USUARIOS ====================

@admin.register(UsuarioAdmin)
class UsuarioAdminAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'rol', 'is_staff', 'is_active')
    list_filter = ('rol', 'is_staff', 'is_active')
    search_fields = ('usuario',)

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('id_cliente', 'usuario', 'correo', 'telefono')
    search_fields = ('usuario', 'correo')
    list_filter = ('usuario',)

# ==================== NEGOCIO - PRODUCTOS ====================

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('id_categoria', 'nombre', 'descripcion')
    search_fields = ('nombre',)

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('id_producto', 'nombre', 'categoria', 'descripcion_corta', 'tiene_imagen')
    list_filter = ('categoria',)
    search_fields = ('nombre', 'descripcion')
    
    def descripcion_corta(self, obj):
        return obj.descripcion[:50] + '...' if len(obj.descripcion) > 50 else obj.descripcion
    descripcion_corta.short_description = 'Descripción'
    
    def tiene_imagen(self, obj):
        return bool(obj.imagen)
    tiene_imagen.boolean = True
    tiene_imagen.short_description = '¿Tiene imagen?'

@admin.register(ProductoVariante)
class ProductoVarianteAdmin(admin.ModelAdmin):
    list_display = ('id_variante', 'producto', 'tamaño', 'precio')
    list_filter = ('tamaño', 'producto__categoria')
    search_fields = ('producto__nombre',)

# ==================== NEGOCIO - SUCURSALES Y EMPLEADOS ====================

    search_fields = ('direccion',)

@admin.register(InventarioSucursal)
class InventarioSucursalAdmin(admin.ModelAdmin):
    list_display = ('id_inventario', 'sucursal', 'variante', 'stock')
    list_filter = ('sucursal', 'variante__producto__categoria')
    search_fields = ('variante__producto__nombre', 'sucursal__direccion')
    list_editable = ('stock',)

@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ('id_empleado', 'nombre', 'apellido', 'cargo', 'estado', 'sucursal')
    list_filter = ('cargo', 'estado', 'sucursal')
    search_fields = ('nombre', 'apellido')

@admin.register(Historial)
class HistorialAdmin(admin.ModelAdmin):
    list_display = ('id_historial', 'empleado', 'pedido', 'detalle', 'fecha')
    list_filter = ('detalle', 'fecha')
    search_fields = ('detalle', 'empleado__nombre')
    date_hierarchy = 'fecha'

# ==================== PROMOCIONES ====================

@admin.register(Promocion)
class PromocionAdmin(admin.ModelAdmin):
    list_display = ('id_promocion', 'titulo', 'precio', 'tiene_imagen')
    search_fields = ('titulo', 'descripcion')
    
    def tiene_imagen(self, obj):
        return bool(obj.imagen)
    tiene_imagen.boolean = True
    tiene_imagen.short_description = '¿Tiene imagen?'

@admin.register(PromocionDetalle)
class PromocionDetalleAdmin(admin.ModelAdmin):
    list_display = ('id_detalle', 'promocion', 'variante', 'cantidad')
    list_filter = ('promocion',)
    search_fields = ('promocion__titulo', 'variante__producto__nombre')

# ==================== CARRITO ====================

@admin.register(Carrito)
class CarritoAdmin(admin.ModelAdmin):
    list_display = ('id_carrito', 'cliente', 'creacion', 'total_items')
    list_filter = ('creacion',)
    search_fields = ('cliente__usuario',)
    date_hierarchy = 'creacion'
    
    def total_items(self, obj):
        return obj.items.count()
    total_items.short_description = 'Total Items'

@admin.register(CarritoItem)
class CarritoItemAdmin(admin.ModelAdmin):
    list_display = ('id_item', 'carrito', 'tipo_item', 'cantidad')
    list_filter = ('carrito__cliente',)
    search_fields = ('carrito__cliente__usuario',)
    
    def tipo_item(self, obj):
        if obj.variante:
            return f"Producto: {obj.variante.producto.nombre} - {obj.variante.tamaño}"
        elif obj.promocion:
            return f"Promoción: {obj.promocion.titulo}"
        return "Sin especificar"
    tipo_item.short_description = 'Item'

# ==================== PEDIDOS ====================

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id_pedido', 'codigo', 'cliente', 'sucursal', 'estado', 'fecha_pedido', 'total')
    list_filter = ('estado', 'fecha_pedido', 'sucursal')
    search_fields = ('codigo', 'cliente__usuario', 'direccion')
    date_hierarchy = 'fecha_pedido'
    readonly_fields = ('fecha_pedido',)
    
    def total(self, obj):
        # Calcula el total sumando los precios de los items
        total = sum(item.precio * item.cantidad for item in obj.items.all())
        return f"${total}"
    total.short_description = 'Total'

@admin.register(PedidoItem)
class PedidoItemAdmin(admin.ModelAdmin):
    list_display = ('id_item', 'pedido', 'tipo_item', 'cantidad', 'precio_unitario', 'subtotal')
    list_filter = ('pedido__estado',)
    search_fields = ('pedido__codigo',)
    
    def tipo_item(self, obj):
        if obj.variante:
            return f"Producto: {obj.variante.producto.nombre} - {obj.variante.tamaño}"
        elif obj.promocion:
            return f"Promoción: {obj.promocion.titulo}"
        return "Sin especificar"
    tipo_item.short_description = 'Item'
    
    def precio_unitario(self, obj):
        return f"${obj.precio}"
    precio_unitario.short_description = 'Precio Unit.'
    
    def subtotal(self, obj):
        return f"${obj.precio * obj.cantidad}"
    subtotal.short_description = 'Subtotal'

# ==================== PAGOS ====================

@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('id_pago', 'pedido', 'monto_formateado', 'metodo_pago', 'estado', 'fecha_pedido')
    list_filter = ('metodo_pago', 'estado')
    search_fields = ('pedido__codigo',)
    date_hierarchy = 'pedido__fecha_pedido'  # Cambiado a pedido__fecha_pedido
    readonly_fields = ('pedido',)
    
    def monto_formateado(self, obj):
        return f"${obj.monto}"
    monto_formateado.short_description = 'Monto'
    
    def fecha_pedido(self, obj):
        return obj.pedido.fecha_pedido
    fecha_pedido.short_description = 'Fecha Pago'
    fecha_pedido.admin_order_field = 'pedido__fecha_pedido'