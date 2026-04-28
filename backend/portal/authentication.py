"""Authentification : accepter le nom d'utilisateur OU l'e-mail (même compte)."""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class EmailOrUsernameBackend(ModelBackend):
    """
    Django envoie la valeur du champ « username » du formulaire ici.
    On accepte soit le username, soit l'e-mail (insensible à la casse).
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        ident = username.strip()
        if not ident:
            return None

        user = User.objects.filter(username__iexact=ident).first()
        if user is None and "@" in ident:
            user = User.objects.filter(email__iexact=ident).first()

        if user is None:
            return None
        if user.check_password(password):
            return user
        return None
