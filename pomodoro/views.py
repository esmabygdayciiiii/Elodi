
import json
import uuid

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import Pomodoro
from todos.models import Todo


@login_required
@require_http_methods(["GET", "POST"])
def save_pomodoro(request):

    today = timezone.localdate()

    # GET: Günlük toplam odak süresini getir
    if request.method == "GET":

        pomodoro = Pomodoro.objects.filter(
            user=request.user,
            date=today
        ).first()

        if pomodoro is None:
            return JsonResponse({
                "status": "success",
                "total_minutes": 0,
                "completed_sessions": 0,
                "formatted_duration": "0 dk",
            })

        return JsonResponse({
            "status": "success",
            "total_minutes": pomodoro.total_minutes,
            "completed_sessions": pomodoro.completed_sessions,
            "formatted_duration": pomodoro.formatted_duration,
        })

    # POST: Tamamlanan Pomodoro süresini kaydet
    try:
        data = json.loads(request.body or "{}")
        minutes = int(data.get("minutes", 25))

        if minutes <= 0 or minutes > 180:
            return JsonResponse({
                "status": "error",
                "message": "Geçersiz süre"
            }, status=400)

        task_id = data.get("task_id")
        
        with transaction.atomic():

            # Görev seçilmişse önce görevin kullanıcıya ait olduğunu kontrol et
            todo = None

            if task_id:
                try:
                    task_id = uuid.UUID(str(task_id))
                except (ValueError, TypeError, AttributeError):
                    return JsonResponse({
                        "status": "error",
                        "message": "Geçersiz görev ID"
                    }, status=400)

                todo = Todo.objects.filter(
                    id=task_id,
                    user=request.user
                ).first()

                if todo is None:
                    return JsonResponse({
                        "status": "error",
                        "message": "Görev bulunamadı."
                    }, status=404)

                # Görevin toplam çalışma süresini artır
                Todo.objects.filter(
                    id=todo.id,
                    user=request.user
                ).update(
                    total_focus_minutes=F("total_focus_minutes") + minutes,
                    updated_at=timezone.now()
                )

                todo.refresh_from_db(
                    fields=["total_focus_minutes"]
                )

            # Günlük Pomodoro kaydını bul veya oluştur
            pomodoro, created = Pomodoro.objects.get_or_create(
                user=request.user,
                date=today
            )

            # Günlük toplam süreyi artır
            Pomodoro.objects.filter(pk=pomodoro.pk).update(
                total_minutes=F("total_minutes") + minutes,
                completed_sessions=F("completed_sessions") + 1
            )

            pomodoro.refresh_from_db()

        return JsonResponse({
            "status": "success",
            "total_minutes": pomodoro.total_minutes,
            "completed_sessions": pomodoro.completed_sessions,
            "formatted_duration": pomodoro.formatted_duration,
            "task_total_minutes": (
                todo.total_focus_minutes if todo else None
            )
        })

    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({
            "status": "error",
            "message": "Geçersiz veri"
        }, status=400)
