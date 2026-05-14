import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pizzas.settings')
django.setup()

import mercadopago
from django.conf import settings
from api.models import Pedido

def test_mp_preference():
    pedido = Pedido.objects.last()
    if not pedido:
        print("No pedido found")
        return

    sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
    
    total_float = 100.0 # Mock total
    
    preference_data = {
        "items": [
            {
                "title": f"Pizza Total - {pedido.codigo}",
                "quantity": 1,
                "unit_price": round(total_float, 2),
                "currency_id": "PEN"
            }
        ],
        "external_reference": str(pedido.id_pedido),
        "back_urls": {
            "success": f"{settings.SITE_URL}/pedidos",
            "failure": f"{settings.SITE_URL}/carrito",
            "pending": f"{settings.SITE_URL}/pedidos"
        },
        "auto_return": "all",
    }
    
    print(f"Testing with data: {preference_data}")
    
    response = sdk.preference().create(preference_data)
    print(f"Status: {response['status']}")
    print(f"Response: {response['response']}")

if __name__ == "__main__":
    test_mp_preference()
