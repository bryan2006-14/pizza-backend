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
        # DEBUG: Ver cookies que llegan
        access_token = request.COOKIES.get('access_token')
        print(f"--- AUTH DEBUG: access_token cookie: {access_token[:20] if access_token else 'MISSING'} ---")
        
        if access_token:
            try:
                # Pasar el token al autenticador JWT de Simple JWT
                jwt_auth = JWTAuthentication()
                validated_token = jwt_auth.get_validated_token(access_token)
                print(f"--- AUTH DEBUG: Token validado. Claims: {validated_token} ---")
                
                # Intentar obtener el usuario del token (buscando en UsuarioAdmin)
                try:
                    user = jwt_auth.get_user(validated_token)
                    if user:
                        return (user, validated_token)
                except:
                    pass

                # Si no es un UsuarioAdmin, buscamos en la tabla Cliente
                from .models import Cliente
                user_id = validated_token.get('user_id')
                if user_id:
                    try:
                        cliente = Cliente.objects.get(id_cliente=user_id)
                        # Agregamos atributos que DRF espera
                        cliente.is_authenticated = True
                        return (cliente, validated_token)
                    except Cliente.DoesNotExist:
                        pass
                
                return None
            except Exception:
                return None
        return None