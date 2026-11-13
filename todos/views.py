
import uuid
from datetime import timezone as dt_timezone

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Category, Todo
from .serializers import CategorySerializer, TodoSerializer
from pomodoro.models import Pomodoro


def _parse_dt(raw, name):
    """ISO 8601 tarih okur. Saat dilimi yoksa UTC kabul eder."""

    try:
        dt = parse_datetime(raw)
    except (ValueError, TypeError):
        dt = None

    if dt is None:
        raise ValidationError({
            name: "Geçersiz tarih. ISO 8601 kullanın (örn. 2026-11-11T10:00:00Z)."
        })

    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, dt_timezone.utc)

    return dt


class OwnedModelViewSet(viewsets.ModelViewSet):
    """Kullanıcı sadece kendi kayıtlarını görür ve değiştirir."""

    model = None

    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        instance.soft_delete()


class CategoryViewSet(OwnedModelViewSet):
    model = Category
    serializer_class = CategorySerializer

    @transaction.atomic
    def perform_destroy(self, instance):
        Todo.all_objects.filter(category=instance).update(
            category=None,
            updated_at=timezone.now()
        )

        instance.soft_delete()


class TodoViewSet(OwnedModelViewSet):
    model = Todo
    serializer_class = TodoSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        completed = params.get("completed")

        if completed in ("true", "1"):
            qs = qs.filter(completed_at__isnull=False)

        elif completed in ("false", "0"):
            qs = qs.filter(completed_at__isnull=True)

        category = params.get("category")

        if category == "none":
            qs = qs.filter(category__isnull=True)

        elif category:
            try:
                qs = qs.filter(category_id=uuid.UUID(category))

            except ValueError:
                raise ValidationError({
                    "category": "Geçersiz kategori id'si."
                })

        priority = params.get("priority")

        if priority:
            if not priority.isdigit():
                raise ValidationError({
                    "priority": "Öncelik bir sayı olmalıdır."
                })

            qs = qs.filter(priority=int(priority))

        if params.get("due_before"):
            qs = qs.filter(
                due_at__lt=_parse_dt(
                    params["due_before"],
                    "due_before"
                )
            )

        if params.get("due_after"):
            qs = qs.filter(
                due_at__gte=_parse_dt(
                    params["due_after"],
                    "due_after"
                )
            )

        if params.get("overdue") in ("true", "1"):
            qs = qs.filter(
                completed_at__isnull=True,
                due_at__lt=timezone.now()
            )

        search = params.get("search")

        if search:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )

        return qs

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        todo = self.get_object()
        todo.complete()

        return Response(self.get_serializer(todo).data)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        todo = self.get_object()
        todo.reopen()

        return Response(self.get_serializer(todo).data)


class SyncPullView(APIView):

    def get(self, request):
        server_time = timezone.now()

        categories = Category.all_objects.filter(
            user=request.user
        )

        todos = Todo.all_objects.filter(
            user=request.user
        )

        since = request.query_params.get("since")

        if since:
            since_dt = _parse_dt(since, "since")

            categories = categories.filter(
                updated_at__gt=since_dt
            )

            todos = todos.filter(
                updated_at__gt=since_dt
            )

        context = {"request": request}

        return Response({
            "server_time": server_time,

            "categories": CategorySerializer(
                categories.order_by("updated_at"),
                many=True,
                context=context
            ).data,

            "todos": TodoSerializer(
                todos.order_by("updated_at"),
                many=True,
                context=context
            ).data,
        })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def save_pomodoro(request):
    """
    GET: Bugünün toplam Pomodoro süresini getirir.
    POST: Tamamlanan Pomodoro seansını kaydeder.
    """

    today = timezone.localdate()

    # GET: Günlük toplam odak süresini getir
    if request.method == 'GET':

        pomodoro = Pomodoro.objects.filter(
            user=request.user,
            date=today
        ).first()

        if pomodoro is None:
            return Response({
                'status': 'success',
                'total_minutes': 0,
                'completed_sessions': 0,
                'formatted_duration': '0 dk',
            })

        return Response({
            'status': 'success',
            'total_minutes': pomodoro.total_minutes,
            'completed_sessions': pomodoro.completed_sessions,
            'formatted_duration': pomodoro.formatted_duration,
        })

    # POST: Tamamlanan Pomodoro süresini kaydet
    if request.method == 'POST':

        try:
            minutes = int(request.data.get('minutes', 25))

        except (ValueError, TypeError):
            return Response(
                {'detail': 'Geçersiz süre değeri.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if minutes <= 0:
            return Response(
                {'detail': 'Geçersiz süre değeri.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        task_id = request.data.get('task_id')

        pomodoro, created = Pomodoro.objects.get_or_create(
            user=request.user,
            date=today
        )

        pomodoro.total_minutes += minutes
        pomodoro.completed_sessions += 1
        pomodoro.save()

        task_total_minutes = None

        if task_id:
            try:
                todo_item = Todo.objects.get(
                    pk=task_id,
                    user=request.user
                )

                todo_item.total_focus_minutes = (
                    todo_item.total_focus_minutes or 0
                ) + minutes

                todo_item.save(
                    update_fields=['total_focus_minutes']
                )

                task_total_minutes = todo_item.total_focus_minutes

            except Todo.DoesNotExist:
                pass

        return Response({
            'status': 'success',
            'detail': 'Pomodoro başarıyla kaydedildi.',
            'total_minutes': pomodoro.total_minutes,
            'completed_sessions': pomodoro.completed_sessions,
            'formatted_duration': pomodoro.formatted_duration,
            'task_total_minutes': task_total_minutes,
        }, status=status.HTTP_200_OK)
