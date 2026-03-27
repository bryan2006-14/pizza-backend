import os
import sys
import django

# Añadir el directorio actual al path para que encuentre los módulos
sys.path.append(os.getcwd())

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pizzas.settings')
django.setup()

from api.models import Promocion, PromocionDetalle, Categoria, ProductoVariante

def populate_promos_final():
    print("Iniciando población de detalles de promociones...")

    try:
        cat_pizza = Categoria.objects.get(nombre__icontains='Pizza')
        cat_bebida = Categoria.objects.get(nombre__icontains='Bebida')
    except Categoria.DoesNotExist as e:
        print(f"Error: Categorías base no encontradas. {e}")
        return

    # 1. Definir las promociones con los tamaños exactos según los IDs actuales
    promociones_config = [
        {
            'id': 1, # Combo Familiar
            'pizzas': {'size': 'familiar', 'qty': 2},
            'drinks': {'size': '1.5L', 'qty': 1}
        },
        {
            'id': 2, # Combo Parejas
            'pizzas': {'size': 'personal', 'qty': 2},
            'drinks': {'size': '500ml', 'qty': 2}
        },
        {
            'id': 3, # Pizza + Bebida (Personal)
            'pizzas': {'size': 'personal', 'qty': 1},
            'drinks': {'size': '500ml', 'qty': 1}
        },
        {
            'id': 4, # Pizza + Bebida 2 (Mediana)
            'pizzas': {'size': 'mediana', 'qty': 1},
            'drinks': {'size': '500ml', 'qty': 1}
        },
    ]

    for config in promociones_config:
        try:
            promo = Promocion.objects.get(id_promocion=config['id'])
            # Borrar detalles viejos
            PromocionDetalle.objects.filter(promocion=promo).delete()
            print(f"\n--- Configurando: {promo.titulo} (ID: {promo.id_promocion}) ---")

            # Agregar todas las variantes de PIZZA de ese tamaño
            pizzas = ProductoVariante.objects.filter(
                producto__categoria=cat_pizza, 
                tamaño__icontains=config['pizzas']['size']
            )
            for v in pizzas:
                PromocionDetalle.objects.create(promocion=promo, variante=v, cantidad=config['pizzas']['qty'])
                print(f"  [Pizza] {v.producto.nombre} ({v.tamaño})")

            # Agregar todas las variantes de BEBIDA de ese tamaño
            drinks = ProductoVariante.objects.filter(
                producto__categoria=cat_bebida, 
                tamaño__icontains=config['drinks']['size']
            )
            for v in drinks:
                PromocionDetalle.objects.create(promocion=promo, variante=v, cantidad=config['drinks']['qty'])
                print(f"  [Bebida] {v.producto.nombre} ({v.tamaño})")

        except Promocion.DoesNotExist:
            print(f"Saltando ID {config['id']}: No encontrado en la base de datos.")

    print("\n✅ Proceso finalizado. Todas las promociones tienen sus detalles registrados.")

if __name__ == "__main__":
    populate_promos_final()
