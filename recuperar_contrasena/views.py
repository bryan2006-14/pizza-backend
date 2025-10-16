from django.shortcuts import render
from api.models import Cliente
from django.conf import settings
from django.core.mail import send_mail
from .utils import cliente_token_generator
from django.shortcuts import render
from rest_framework.permissions import AllowAny
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from django.contrib.auth.hashers import make_password

class SolicitarRecuperacionContrasena(APIView):
    def post(self, request):
        correo = request.data.get("correo")
        
        if not correo:
            return Response({"error": "El correo es obligatorio."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            cliente = Cliente.objects.get(correo=correo)
        except Cliente.DoesNotExist:
            return Response({"error": "Cliente no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        
        token = cliente_token_generator.make_token(cliente)
        recovery_link = f"{settings.SITE_URL}/recovery/reset/{cliente.id_cliente}/{token}/"
        
        subject = "Recuperación de contraseña | Happy Pizza"
        html_content = f"""
        <p>Hola {cliente.usuario},</p>
        <p>Haz clic en el siguiente enlace para restablecer su contraseña:</p>
        <a href="{recovery_link}">Restablecer mi contraseña</a>
        """
        
        try:
            send_mail(
                subject,
                '',
                settings.EMAIL_HOST_USER,
                [cliente.correo],
                fail_silently=False,
                html_message=html_content
            )
            return Response({"message": "Correo de recuperación enviado."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RestablecerContrasena(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [AllowAny]

    def get(self, request, cliente_id, token):
        try:
            cliente = Cliente.objects.get(id_cliente=cliente_id)
        except Cliente.DoesNotExist:
            return Response({"error": "Cliente no encontrado."}, status=404)
        if not cliente_token_generator.check_token(cliente, token):
            return Response({"error": "El enlace de recuperación es inválido o ha caducado."}, status=400)
        return render(request, "recuperar_contrasena/restablecer_contrasena.html", {
            'cliente_id': cliente_id,
            'token': token
        })

    def post(self, request, cliente_id, token):
        try:
            cliente = Cliente.objects.get(id_cliente=cliente_id)
        except Cliente.DoesNotExist:
            return Response({"error": "Cliente no encontrado."}, status=404)
        if not cliente_token_generator.check_token(cliente, token):
            return Response({"error": "El enlace de recuperación es inválido o ha caducado."}, status=400)

        nueva_contrasena = request.POST.get("password")
        cliente.contrasena = make_password(nueva_contrasena)
        cliente.save()
        return render(request, "recuperar_contrasena/restablecer_contrasena.html", {
            'cliente_id': cliente_id,
            'token': token,
            'success_message': "Contraseña actualizada"
        })