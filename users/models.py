
import uuid

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower


username_validator = RegexValidator(
    regex=r"^[a-z0-9\_.]{3,50}$",
    message="Kullanıcı adı 3-50 karakter olmalı; yalnızca küçük harf, rakam, _ ve . içerebilir.",
)


class CustomUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, username, password, **extra_fields):
        if not username:
            raise ValueError("Kullanıcı adı zorunludur")

        username = username.strip().lower()

        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.full_clean(exclude=["password"])
        user.save(using=self._db)
        return user

    def create_user(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(username, password, **extra_fields)

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser is_staff=True olmalıdır")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser is_superuser=True olmalıdır")

        return self._create_user(username, password, **extra_fields)

    def get_by_natural_key(self, username):
        return self.get(username__iexact=username)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    username = models.CharField(
        max_length=50, unique=True, validators=[username_validator]
    )

    # Kullanıcının site içerisinde görünen takma adı
    nick = models.CharField(
        max_length=50,
        blank=True,
        default="",
        verbose_name="Takma ad"
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "Kullanıcı"
        verbose_name_plural = "Kullanıcılar"
        constraints = [
            models.UniqueConstraint(Lower("username"), name="uniq_user_username_ci"),
        ]

    def clean(self):
        super().clean()
        if self.username:
            self.username = self.username.strip().lower()

    def get_full_name(self):
        return self.username

    def get_short_name(self):
        return self.username

    def __str__(self):
        return self.username
