"""Authenticate with either the username or the e-mail address."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class EmailOrUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        identifier = username or kwargs.get(UserModel.USERNAME_FIELD)
        if identifier is None or password is None:
            return None
        try:
            user = UserModel.objects.get(
                Q(username__iexact=identifier) | Q(email__iexact=identifier)
            )
        except UserModel.DoesNotExist:
            UserModel().set_password(password)  # timing attack mitigation
            return None
        except UserModel.MultipleObjectsReturned:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
