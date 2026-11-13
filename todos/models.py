import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone


hex_color_validator = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="Renk #RRGGBB formatında olmalıdır (örn. #FF8800).",
)


class AliveManager(models.Manager):
    """Silinmemiş kayıtları döndürür (günlük kullanım için)."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class SyncModel(models.Model):
    """Senkronizasyon için ortak alanlar.

    - id: istemci (mobil/web/windows) offline iken kendi UUID'sini üretebilir
    - updated_at: "şu tarihten sonra değişenleri ver" sorgusu için
    - deleted_at: soft delete; silinen kaydı diğer cihazlara da bildirebilmek için
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = AliveManager()      # silinmemişler
    all_objects = models.Manager()  # silinenler dahil (sync için)

    class Meta:
        abstract = True

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=["deleted_at", "updated_at"])


class Category(SyncModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="categories",
    )
    name = models.CharField(max_length=50)
    color = models.CharField(
        max_length=7, default="#6C8EF5", validators=[hex_color_validator]
    )
    icon = models.CharField(max_length=30, blank=True)  # ikon anahtarı, örn. "book"
    position = models.FloatField(default=0)  # sıralama

    class Meta:
        verbose_name = "Kategori"
        verbose_name_plural = "Kategoriler"
        ordering = ["position", "created_at"]
        constraints = [
            # Aynı kullanıcıda aynı isimde (harf duyarsız) iki aktif kategori olmasın
            models.UniqueConstraint(
                Lower("name"),
                "user",
                condition=Q(deleted_at__isnull=True),
                name="uniq_category_name_per_user",
            ),
        ]

    def __str__(self):
        return self.name



class Todo(SyncModel):
    class Priority(models.IntegerChoices):
        LOW = 1, "Düşük"
        MEDIUM = 2, "Orta"
        HIGH = 3, "Yüksek"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="todos",
    )

    # Kategori silinirse görevler silinmesin
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="todos",
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    priority = models.PositiveSmallIntegerField(
        choices=Priority.choices,
        default=Priority.MEDIUM
    )

    due_at = models.DateTimeField(null=True, blank=True)

    # Görevin tamamlanma tarihi
    completed_at = models.DateTimeField(null=True, blank=True)

    # Sürükle-bırak sıralama
    position = models.FloatField(default=0)

    # Görev için toplam çalışılan süre (dakika)
    total_focus_minutes = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Görev"
        verbose_name_plural = "Görevler"
        ordering = ["position", "-created_at"]

        indexes = [
            models.Index(fields=["user", "completed_at"]),
            models.Index(fields=["user", "due_at"]),
            models.Index(fields=["user", "updated_at"]),
        ]

        constraints = [
            models.CheckConstraint(
                condition=~Q(title=""),
                name="todo_title_not_empty"
            ),
        ]

    def __str__(self):
        return self.title

    @property
    def is_completed(self):
        return self.completed_at is not None

    @property
    def is_overdue(self):
        return (
            not self.is_completed
            and self.due_at is not None
            and self.due_at < timezone.now()
        )

    def complete(self):
        if not self.is_completed:
            self.completed_at = timezone.now()
            self.save(update_fields=["completed_at", "updated_at"])

    def reopen(self):
        if self.is_completed:
            self.completed_at = None
            self.save(update_fields=["completed_at", "updated_at"])

    def clean(self):
        super().clean()

        # Başkasının kategorisine görev eklenemesin
        if self.category_id and self.category.user_id != self.user_id:
            raise ValidationError({
                "category": "Bu kategori size ait değil."
            })
