import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pizzas.settings')
django.setup()

from api.models import Cliente, Sucursal, Pedido, Carrito, CarritoItem, ProductoVariante, Producto, Categoria
from api.serializers import PedidoSerializer
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

def test_pedido_creation():
    cliente = Cliente.objects.first()
    sucursal = Sucursal.objects.first()
    
    if not cliente or not sucursal:
        print("Missing data to test")
        return

    import time
    data = {
        "sucursal": sucursal.id_sucursal,
        "direccion": "Test Address",
        "cliente": cliente.id_cliente,
        "codigo": f"TEST-CODE-{int(time.time())}",
        "estado": "pendiente_pago",
        "tipo_entrega": "delivery",
        "costo_delivery": "5.00"
    }

    serializer = PedidoSerializer(data=data)
    if serializer.is_valid():
        print("Serializer is valid")
        try:
            pedido = serializer.save()
            print(f"Pedido created: {pedido.id_pedido}")
            
            # Simulate perform_create
            items_data = [] # Empty as in frontend
            
            if not items_data:
                print("Looking in Carrito DB...")
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
            
            print(f"Items to create: {len(items_data)}")
            from api.models import PedidoItem, PedidoItemOpcion
            for i, item in enumerate(items_data):
                print(f"Creating item {i}: {item}")
                pedido_item = PedidoItem.objects.create(
                    pedido=pedido,
                    variante_id=item.get('variante'),
                    promocion_id=item.get('promocion'),
                    cantidad=item.get('cantidad', 1),
                    precio=item.get('precio') or 0
                )
                print(f"Created PedidoItem: {pedido_item.id_item}")
                
                opciones = item.get('opciones', [])
                for j, opc in enumerate(opciones):
                    print(f"Creating option {j}: {opc}")
                    PedidoItemOpcion.objects.create(
                        pedido_item=pedido_item,
                        variante_id=opc.get('variante'),
                        cantidad=opc.get('cantidad', 1)
                    )
            print("Cleanup...")
            # Carrito.objects.filter(cliente=pedido.cliente).delete()
            print("SUCCESS")
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"Serializer errors: {serializer.errors}")

if __name__ == "__main__":
    test_pedido_creation()
