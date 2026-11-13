
import logging
from datetime import datetime

from django.conf import settings
from django.shortcuts import render
from django.contrib.auth import get_user_model
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum
from django.utils import timezone

from todos.models import Todo, Category
from pomodoro.models import Pomodoro

User = get_user_model()


def get_system_logs():
    log_file = settings.LOG_DIR / "elodi.log"
    system_logs = []

    if not log_file.exists():
        return system_logs

    try:
        lines = log_file.read_text(
            encoding="utf-8",
            errors="replace"
        ).splitlines()

        for line in reversed(lines[-100:]):
            parts = line.split(" | ", 3)

            if len(parts) != 4:
                continue

            level, date_text, logger_name, message = parts

            try:
                created_at = datetime.strptime(
                    date_text,
                    "%Y-%m-%d %H:%M:%S,%f"
                )

                created_at = timezone.make_aware(
                    created_at,
                    timezone.get_current_timezone()
                )

            except ValueError:
                continue

            system_logs.append({
                "level": level,
                "action": logger_name,
                "description": message,
                "user": None,
                "created_at": created_at,
            })

    except OSError:
        logging.getLogger(__name__).exception(
            "System log file could not be read."
        )

    return system_logs


@staff_member_required(login_url="/login/")
def admin_dashboard(request):

    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()

    # Görev istatistikleri
    total_tasks = Todo.objects.count()

    completed_tasks = Todo.objects.filter(
        completed_at__isnull=False
    ).count()

    pending_tasks = Todo.objects.filter(
        completed_at__isnull=True
    ).count()

    # Kategori sayısı
    total_categories = Category.objects.count()

    # Pomodoro istatistikleri
    pomodoro_stats = Pomodoro.objects.aggregate(
        total_minutes=Sum("total_minutes"),
        total_sessions=Sum("completed_sessions")
    )

    total_focus_minutes = pomodoro_stats["total_minutes"] or 0
    total_sessions = pomodoro_stats["total_sessions"] or 0

    # Son kayıt olan kullanıcılar
    recent_users = User.objects.order_by("-created_at")[:5]

    # Tüm kullanıcılar
    all_users = User.objects.order_by("-created_at")

    # Son oluşturulan görevler
    recent_tasks = Todo.objects.select_related(
        "user"
    ).order_by("-created_at")[:5]

    # Sistem logları
    system_logs = get_system_logs()

    context = {
        "total_users": total_users,
        "active_users": active_users,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "total_categories": total_categories,
        "total_focus_minutes": total_focus_minutes,
        "total_sessions": total_sessions,
        "recent_users": recent_users,
        "recent_tasks": recent_tasks,
        "all_users": all_users,
        "system_logs": system_logs,
    }

    return render(
        request,
        "admin_dashboard.html",
        context
    )
