from django.contrib.auth.tokens import PasswordResetTokenGenerator

class ClienteTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, cliente, timestamp):
        return str(cliente.id_cliente) + str(timestamp)
cliente_token_generator = ClienteTokenGenerator()