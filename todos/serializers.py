from rest_framework import serializers

from .models import Category, Todo


class ClientIdMixin:
    """İstemci (offline) kendi UUID'sini üretip gönderebilir.

    - Oluştururken: id verilebilir, ama başka bir kayda ait olamaz.
    - Güncellerken: id asla değiştirilemez.
    """

    def validate_id(self, value):
        if self.instance is None and self.Meta.model.all_objects.filter(pk=value).exists():
            raise serializers.ValidationError("Bu id zaten kullanılıyor.")
        return value

    def update(self, instance, validated_data):
        validated_data.pop("id", None)
        return super().update(instance, validated_data)


class OwnedCategoryField(serializers.PrimaryKeyRelatedField):
    """Sadece isteği yapan kullanıcının (silinmemiş) kategorileri seçilebilir."""

    def get_queryset(self):
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return Category.objects.none()
        return Category.objects.filter(user=request.user)


class CategorySerializer(ClientIdMixin, serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)

    class Meta:
        model = Category
        fields = (
            "id", "name", "color", "icon", "position",
            "created_at", "updated_at", "deleted_at",
        )
        read_only_fields = ("created_at", "updated_at", "deleted_at")

    def validate_name(self, value):
        value = value.strip()
        qs = Category.objects.filter(
            user=self.context["request"].user, name__iexact=value
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Bu isimde bir kategoriniz zaten var.")
        return value


class TodoSerializer(ClientIdMixin, serializers.ModelSerializer):
    id = serializers.UUIDField(required=False)
    category = OwnedCategoryField(allow_null=True, required=False)
    is_completed = serializers.BooleanField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    # Göreve ait toplam odaklanma süresi
    total_focus_minutes = serializers.IntegerField(read_only=True)

    class Meta:
        model = Todo
        fields = (
            "id",
            "title",
            "description",
            "category",
            "priority",
            "due_at",
            "completed_at",
            "is_completed",
            "is_overdue",
            "total_focus_minutes",  # Buraya ekledik
            "position",
            "created_at",
            "updated_at",
            "deleted_at",
        )
        read_only_fields = ("created_at", "updated_at", "deleted_at")