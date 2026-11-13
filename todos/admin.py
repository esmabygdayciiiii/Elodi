from django.contrib import admin

from .models import Category, Todo


class SoftDeleteAdmin(admin.ModelAdmin):
    """Admin panelinde silinmiş (soft delete) kayıtlar da görünür."""

    readonly_fields = ("id", "created_at", "updated_at")

    def get_queryset(self, request):
        qs = self.model.all_objects.get_queryset()
        ordering = self.get_ordering(request)
        return qs.order_by(*ordering) if ordering else qs

    @admin.display(boolean=True, description="Silindi")
    def is_deleted(self, obj):
        return obj.deleted_at is not None


@admin.register(Category)
class CategoryAdmin(SoftDeleteAdmin):
    list_display = ("name", "user", "color", "is_deleted", "updated_at")
    search_fields = ("name", "user__email")


@admin.register(Todo)
class TodoAdmin(SoftDeleteAdmin):
    list_display = (
        "title", "user", "category", "priority",
        "due_at", "completed_at", "is_deleted",
    )
    list_filter = ("priority",)
    search_fields = ("title", "user__email")