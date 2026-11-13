from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    """Admin panelinde yeni kullanıcı eklerken sadece username istenir."""
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ("username",)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm

    list_display = (
        "username", "is_active", "is_staff", "created_at",
    )
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("username",)
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "last_login")

    fieldsets = (
        (None, {"fields": ("id", "username", "password")}),
        ("Durum", {"fields": ("is_active",)}),
        (
            "Yetkiler",
            {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Tarihler", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username", "password1", "password2",
                ),
            },
        ),
    )