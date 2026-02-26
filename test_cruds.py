import os
import sys
import django

# Redirect stdout to a file to prevent truncation
log_file = open('test_cruds_output.log', 'w', encoding='utf-8')
sys.stdout = log_file

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pizzas.settings')
django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS.append('testserver')

from django.test import Client
from django.urls import reverse
from api.models import UsuarioAdmin

client = Client()
# Log in as a superuser to bypass LoginRequiredMixin
try:
    user = UsuarioAdmin.objects.get(usuario='admin')
except:
    user = UsuarioAdmin.objects.create_superuser('admin', 'admin')

client.force_login(user)

urls_to_test = [
    'usuarioadmins_lista', 'clientes_lista', 'categorias_lista', 
    'productos_lista', 'productosvariantes_lista', 'sucursales_lista', 
    'empleados_lista', 'historial_lista', 'promociones_lista', 
    'promocionesdetalle_lista', 'carritos_lista', 'carritositems_lista', 
    'pedidos_lista', 'pedidositems_lista', 'pagos_lista'
]

print("\n--- TEST LIST VIEWS ---")
for url_name in urls_to_test:
    try:
        url = reverse(url_name)
        response = client.get(url)
        if response.status_code == 200:
            print(f"[OK] {url_name}")
        else:
            print(f"[FAIL] {url_name} (Status: {response.status_code})")
    except Exception as e:
        import traceback
        print(f"[ERROR] {url_name}\n{traceback.format_exc()}")

model_names = [
    'usuarioadmins', 'clientes', 'categorias', 'productos', 
    'productosvariantes', 'sucursales', 'empleados', 'historial', 
    'promociones', 'promocionesdetalle', 'carritos', 'carritositems', 
    'pedidos', 'pedidositems', 'pagos'
]

print("\n--- TEST CREATE VIEWS ---")
for m_name in model_names:
    try:
        url = reverse('crear_objeto', kwargs={'model_name': m_name})
        response = client.get(url)
        if response.status_code == 200:
            print(f"[OK] crear {m_name}")
        else:
            print(f"[FAIL] crear {m_name} (Status: {response.status_code})")
    except Exception as e:
        import traceback
        print(f"[ERROR] crear {m_name}\n{traceback.format_exc()}")

log_file.close()
