import os
import sys
import django

# Añadir el directorio base al path de Python
sys.path.append(os.getcwd())

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pizzas.settings')
django.setup()

from api.models import Sucursal, ProductoVariante, InventarioSucursal

def populate():
    print("Iniciando carga de inventario...")
    sucursales = Sucursal.objects.all()
    variantes = ProductoVariante.objects.all()
    
    if not sucursales:
        print("Error: No hay sucursales registradas.")
        return
    
    if not variantes:
        print("Error: No hay variantes de productos registradas.")
        return

    count_creado = 0
    count_actualizado = 0
    total_unidades = 50

    for s in sucursales:
        print(f"--- Procesando Sucursal: {s.direccion} ---")
        for v in variantes:
            # Buscamos si ya existe el registro, si no lo creamos con stock inicial
            obj, created = InventarioSucursal.objects.get_or_create(
                sucursal=s,
                variante=v,
                defaults={'stock': total_unidades}
            )
            
            if created:
                count_creado += 1
            else:
                # Si ya existía pero con stock 0, le damos el inicial de 50
                if obj.stock == 0:
                    obj.stock = total_unidades
                    obj.save()
                    count_actualizado += 1
    
    print("\nResumen:")
    print(f"- Registros nuevos creados: {count_creado}")
    print(f"- Registros actualizados (de 0 a 50): {count_actualizado}")
    print(f"- Total de registros en Inventario Sucursal: {InventarioSucursal.objects.count()}")

if __name__ == '__main__':
    populate()
