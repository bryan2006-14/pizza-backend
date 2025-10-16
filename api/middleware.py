# append_slash_middleware.py
from django.http import HttpResponsePermanentRedirect
from django.utils.deprecation import MiddlewareMixin
from rest_framework.authentication import BaseAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication

class AppendSlashMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not request.path.endswith('/'):
            print(f"\nMétodo HTTP: {request.method}")
            print(f"Ruta: {request.get_full_path()}")
            
            # Imprime las cabeceras
            print("\nHEADERS:")
            for header, value in request.headers.items():
                print(f"{header}: {value}")
            
            # Imprime el cuerpo de la solicitud (si existe y es POST o PUT)
            if request.method in ('POST', 'PUT') and request.body:
                print("\nBODY:")
                print(request.body.decode('utf-8'))  # Decodifica para ver el texto
                
            request.path_info = request.path + '/'


class CookieJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        # Extraer token de la cookie
        access_token = request.COOKIES.get('access_token')
        
        if access_token:
            try:
                # Pasar el token al autenticador JWT de Simple JWT
                validated_token = JWTAuthentication().get_validated_token(access_token)
                user = JWTAuthentication().get_user(validated_token)
                return (user, validated_token)
            except Exception:
                return None
        return None