from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

# ==================== USUARIOS ====================

class UsuarioAdminManager(BaseUserManager):
    def create_user(self, usuario, password=None, **extra_fields):
        if not usuario:
            raise ValueError('El usuario debe tener un nombre de usuario')
        extra_fields.setdefault('is_active', True)
        user = self.model(usuario=usuario, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, usuario, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superusuario debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superusuario debe tener is_superuser=True.')

        return self.create_user(usuario, password, **extra_fields)

    def get_by_natural_key(self, usuario):
        return self.get(usuario=usuario)

class UsuarioAdmin(AbstractBaseUser, PermissionsMixin):
    ROL_CHOICES = [
        ('general', 'General'),
        ('otro', 'Otro'),
    ]

    usuario = models.CharField(max_length=1024, unique=True)
    rol = models.CharField(max_length=10, choices=ROL_CHOICES)
    is_staff = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    USERNAME_FIELD = 'usuario'
    REQUIRED_FIELDS = []

    objects = UsuarioAdminManager()

    def __str__(self):
        return self.usuario
    
    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

class Cliente(models.Model):
    id_cliente = models.AutoField(primary_key=True)
    usuario = models.CharField(max_length=45, unique=True)
    correo = models.EmailField(max_length=50, unique=True)
    telefono = models.IntegerField()  # En la imagen es string, podrías cambiarlo a CharField
    contrasena = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.id_cliente} - {self.usuario}"
    
    class Meta:
        db_table = 'clientes'

# ==================== NEGOCIO - PRODUCTOS ====================

class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=45)
    descripcion = models.CharField(max_length=300)

    def __str__(self):
        return f"{self.id_categoria} - {self.nombre}"
    
    class Meta:
        db_table = 'categorias'

class Producto(models.Model):
    id_producto = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=45)
    descripcion = models.CharField(max_length=300)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, db_column='categoria_id')
    # imagen no estaba en tu modelo original pero está en la imagen
    imagen = models.ImageField(upload_to='productos/', null=True, blank=True)

    class Meta:
        db_table = 'productos'

    def __str__(self):
        return f"{self.id_producto} - {self.nombre}"

class ProductoVariante(models.Model):
    
    id_variante = models.AutoField(primary_key=True)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, db_column='producto_id', related_name='variantes')
    tamaño = models.CharField(max_length=100) 
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    # El stock ahora se maneja por sucursal en la tabla InventarioSucursal

    class Meta:
        db_table = 'productos_variante'
        unique_together = (('producto', 'tamaño'),)

    def __str__(self):
        return f"{self.producto.nombre} - {self.tamaño}"

# ==================== NEGOCIO - SUCURSALES Y EMPLEADOS ====================

class Sucursal(models.Model):
    id_sucursal = models.AutoField(primary_key=True)
    telefono = models.IntegerField()  # En la imagen es string, podrías cambiarlo
    direccion = models.CharField(max_length=45)
    hora_inicio = models.TimeField()
    hora_cierre = models.TimeField()

    def __str__(self):
        return f"{self.id_sucursal} - {self.direccion}"
    
    class Meta:
        db_table = 'sucursales'

class InventarioSucursal(models.Model):
    id_inventario = models.AutoField(primary_key=True)
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE, db_column='sucursal_id', related_name='inventarios')
    variante = models.ForeignKey(ProductoVariante, on_delete=models.CASCADE, db_column='variante_id', related_name='stocks_sucursal')
    stock = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'inventarios_sucursal'
        unique_together = (('sucursal', 'variante'),)

    def __str__(self):
        return f"{self.sucursal.direccion} - {self.variante.producto.nombre} ({self.variante.tamaño}): {self.stock}"

class Empleado(models.Model):
    CARGO_CHOICES = [
        ('repartidor', 'Repartidor'),
        ('recepcion', 'Recepcion'),
        ('cocinero', 'Cocinero'),
        ('administrador', 'Administrador')
    ]

    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('vacaciones', 'Vacaciones'),
    ]

    id_empleado = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=45)
    apellido = models.CharField(max_length=45)
    cargo = models.CharField(max_length=45, choices=CARGO_CHOICES)
    estado = models.CharField(max_length=25, choices=ESTADO_CHOICES, default='activo')
    sucursal = models.ForeignKey(Sucursal, on_delete=models.PROTECT, db_column='sucursal_id')

    class Meta:
        db_table = 'empleados'

    def __str__(self):
        return f"{self.nombre} {self.apellido} - {self.cargo}"

class Historial(models.Model):
    DETALLE_CHOICES = [
        ('preparacion', 'Preparación'),
        ('en camino', 'En camino'),
        ('entregando', 'Entregando'),
        ('completado', 'Completado'),
    ]
    
    id_historial = models.AutoField(primary_key=True)
    empleado = models.ForeignKey(Empleado, on_delete=models.PROTECT, db_column='empleado_id')
    pedido = models.ForeignKey('Pedido', on_delete=models.PROTECT, db_column='pedido_id')
    detalle = models.CharField(max_length=45, choices=DETALLE_CHOICES)
    fecha = models.DateField()

    class Meta:
        db_table = 'historial'

    def __str__(self):
        return f"Historial {self.id_historial} - Pedido {self.pedido_id}"

# ==================== PROMOCIONES ====================

class Promocion(models.Model):
    id_promocion = models.AutoField(primary_key=True)
    titulo = models.CharField(max_length=60)
    descripcion = models.CharField(max_length=300)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    imagen = models.ImageField(upload_to='promociones/', null=True, blank=True)

    class Meta:
        db_table = 'promociones'

    def __str__(self):
        return f"{self.id_promocion} - {self.titulo}"

class PromocionDetalle(models.Model):
    id_detalle = models.AutoField(primary_key=True)
    promocion = models.ForeignKey(Promocion, on_delete=models.PROTECT, db_column='promocion_id', related_name='detalles')
    
    # Variante para ítem fijo, o categoria para ítems elegibles
    variante = models.ForeignKey(ProductoVariante, on_delete=models.PROTECT, db_column='variante_id', null=True, blank=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, db_column='categoria_id', null=True, blank=True)
    tamaño = models.CharField(max_length=100, null=True, blank=True) 
    
    cantidad = models.PositiveIntegerField()

    class Meta:
        db_table = 'promociones_detalle'

    def __str__(self):
        return f"Detalle Promo {self.id_detalle}"

# ==================== CARRITO ====================

class Carrito(models.Model):
    id_carrito = models.AutoField(primary_key=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, db_column='cliente_id')
    creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'carritos'
    
    def __str__(self):
        return f"Carrito {self.id_carrito} - Cliente {self.cliente_id}"

class CarritoItem(models.Model):
    id_item = models.AutoField(primary_key=True)
    carrito = models.ForeignKey(Carrito, on_delete=models.PROTECT, db_column='carrito_id', related_name='items')
    variante = models.ForeignKey(ProductoVariante, on_delete=models.PROTECT, db_column='variante_id', null=True, blank=True)
    promocion = models.ForeignKey(Promocion, on_delete=models.PROTECT, db_column='promocion_id', null=True, blank=True)
    cantidad = models.PositiveIntegerField()

    class Meta:
        db_table = 'carritos_item'
        # Asegurar que solo uno de los dos (variante o promocion) esté presente
        constraints = [
            models.CheckConstraint(
                check=(
                    (models.Q(variante__isnull=False) & models.Q(promocion__isnull=True)) |
                    (models.Q(variante__isnull=True) & models.Q(promocion__isnull=False))
                ),
                name='carrito_item_tipo_unico'
            )
        ]

    def __str__(self):
        if self.variante:
            return f"Item {self.id_item} - {self.variante} x{self.cantidad}"
        return f"Item {self.id_item} - {self.promocion.titulo} x{self.cantidad}"

class CarritoItemOpcion(models.Model):
    id_opcion = models.AutoField(primary_key=True)
    carrito_item = models.ForeignKey(CarritoItem, on_delete=models.CASCADE, related_name='opciones_promocion')
    variante = models.ForeignKey(ProductoVariante, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = 'carritos_item_opcion'

    def __str__(self):
        return f"Opción {self.id_opcion} - {self.variante} x{self.cantidad}"

# ==================== PEDIDOS ====================

class Pedido(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('confirmado', 'Confirmado'),
        ('preparando', 'Preparando'),
        ('en_camino', 'En Camino'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
    ]
    
    id_pedido = models.AutoField(primary_key=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, db_column='cliente_id')
    sucursal = models.ForeignKey(Sucursal, on_delete=models.PROTECT, db_column='sucursal_id')
    fecha_pedido = models.DateTimeField(auto_now_add=True)
    fecha_entrega = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=45, choices=ESTADO_CHOICES, default='pendiente')
    direccion = models.CharField(max_length=85)
    codigo = models.CharField(max_length=45, unique=True)

    class Meta:
        db_table = 'pedidos'

    def __str__(self):
        return f"Pedido {self.codigo} - {self.estado}"

class PedidoItem(models.Model):
    id_item = models.AutoField(primary_key=True)
    pedido = models.ForeignKey(Pedido, on_delete=models.PROTECT, db_column='pedido_id', related_name='items')
    variante = models.ForeignKey(ProductoVariante, on_delete=models.PROTECT, db_column='variante_id', null=True, blank=True)
    promocion = models.ForeignKey(Promocion, on_delete=models.PROTECT, db_column='promocion_id', null=True, blank=True)
    cantidad = models.PositiveIntegerField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)  # Precio al momento de la compra

    class Meta:
        db_table = 'pedidos_item'
        # Asegurar que solo uno de los dos (variante o promocion) esté presente
        constraints = [
            models.CheckConstraint(
                check=(
                    (models.Q(variante__isnull=False) & models.Q(promocion__isnull=True)) |
                    (models.Q(variante__isnull=True) & models.Q(promocion__isnull=False))
                ),
                name='pedido_item_tipo_unico'
            )
        ]

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            sucursal = self.pedido.sucursal
            if self.variante:
                inv, created = InventarioSucursal.objects.get_or_create(
                    sucursal=sucursal, 
                    variante=self.variante,
                    defaults={'stock': 0}
                )
                inv.stock = max(0, inv.stock - self.cantidad)
                inv.save()
            
            if self.promocion:
                detalles = self.promocion.detalles.filter(variante__isnull=False)
                for det in detalles:
                    inv, created = InventarioSucursal.objects.get_or_create(
                        sucursal=sucursal,
                        variante=det.variante,
                        defaults={'stock': 0}
                    )
                    inv.stock = max(0, inv.stock - (det.cantidad * self.cantidad))
                    inv.save()

    def __str__(self):
        if self.variante:
            return f"Item {self.id_item} - {self.variante} x{self.cantidad}"
        return f"Item {self.id_item} - {self.promocion.titulo} x{self.cantidad}"

class PedidoItemOpcion(models.Model):
    id_opcion = models.AutoField(primary_key=True)
    pedido_item = models.ForeignKey(PedidoItem, on_delete=models.CASCADE, related_name='opciones_promocion')
    variante = models.ForeignKey(ProductoVariante, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = 'pedidos_item_opcion'

    def __str__(self):
        return f"Opción {self.id_opcion} - {self.variante} x{self.cantidad}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # Descontar stock de la opción elegida en la promoción
            sucursal = self.pedido_item.pedido.sucursal
            inv, created = InventarioSucursal.objects.get_or_create(
                sucursal=sucursal,
                variante=self.variante,
                defaults={'stock': 0}
            )
            cantidad_total = self.cantidad * self.pedido_item.cantidad
            inv.stock = max(0, inv.stock - cantidad_total)
            inv.save()

# ==================== PAGOS ====================

class Pago(models.Model):
    METODO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('transferencia', 'Transferencia'),
    ]

    ESTADO_PAGO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('completado', 'Completado'),
        ('fallido', 'Fallido'),
        ('reembolsado', 'Reembolsado'),
    ]

    id_pago = models.AutoField(primary_key=True)
    pedido = models.OneToOneField(Pedido, on_delete=models.PROTECT, db_column='pedido_id', related_name='pago')
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = models.CharField(max_length=45, choices=METODO_PAGO_CHOICES)
    estado = models.CharField(max_length=45, choices=ESTADO_PAGO_CHOICES, default='pendiente')

    class Meta:
        db_table = 'pagos'

    def __str__(self):
        return f"Pago {self.id_pago} - {self.estado} - ${self.monto}"

# ==================== MODELOS ADICIONALES QUE PODRÍAS ELIMINAR ====================
# (Estos modelos existían en tu código original pero no están en la imagen)
# Puedes eliminarlos si ya no los necesitas:

# Area, TipoRepertorio, Repertorio, ProductoVenta, ProductoPrima, 
# DetalleRepertorio, DetallePedido, Paquete