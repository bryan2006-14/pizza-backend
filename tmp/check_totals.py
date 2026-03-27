import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pizzas.settings')
django.setup()

from api.models import Pedido
from api.serializers import PedidoSerializer

pedidos = Pedido.objects.all()
for p in pedidos:
    data = PedidoSerializer(p).data
    print(f"Pedido: {p.codigo}")
    print(f"  costo_delivery en BD: {p.costo_delivery}")
    print(f"  tipo_entrega en BD:   {p.tipo_entrega}")
    print(f"  total del serializer: {data['total']}")
    print()
