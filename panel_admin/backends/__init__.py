from django.contrib.auth.backends import BaseBackend
from api.models import UsuarioAdmin

class UsuarioAdminBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            usuario = UsuarioAdmin.objects.get(usuario=username)  
            if usuario.check_password(password):
                return usuario
        except UsuarioAdmin.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return UsuarioAdmin.objects.get(pk=user_id)
        except UsuarioAdmin.DoesNotExist:
            return None
