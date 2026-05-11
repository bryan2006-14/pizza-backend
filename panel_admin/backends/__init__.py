"""
panel_admin/backends/__init__.py

Cambios:
  - Manejo explícito de MultipleObjectsReturned (si el campo usuario no es unique)
  - Verificación de is_active antes de devolver el usuario
  - Sin exponer información diferente entre "usuario no existe" y "contraseña incorrecta"
    (el mensaje de error está en la vista, no aquí)
"""

from django.contrib.auth.backends import BaseBackend
from api.models import UsuarioAdmin


class UsuarioAdminBackend(BaseBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        try:
            usuario = UsuarioAdmin.objects.get(usuario=username)
        except UsuarioAdmin.DoesNotExist:
            # Llamada a check_password con hash dummy para no filtrar
            # el tiempo de respuesta y evitar timing attacks
            UsuarioAdmin().set_password(password)
            return None
        except UsuarioAdmin.MultipleObjectsReturned:
            # Campo usuario no es unique: devolver None de forma segura
            return None

        # Verificar contraseña y estado activo en un solo bloque
        if usuario.check_password(password) and self.user_can_authenticate(usuario):
            return usuario
        return None

    def user_can_authenticate(self, user):
        """Respetar is_active (igual que ModelBackend de Django)."""
        is_active = getattr(user, 'is_active', None)
        return is_active or is_active is None

    def get_user(self, user_id):
        try:
            user = UsuarioAdmin.objects.get(pk=user_id)
        except UsuarioAdmin.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None