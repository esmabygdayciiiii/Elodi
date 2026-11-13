
from pathlib import Path

from django.urls import path, include
from django.views.generic import TemplateView
from django.http import FileResponse


def google_site_verification(request):
    file_path = (
        Path(__file__).resolve().parent.parent
        / "googlebf6b22f221e979ef.html"
    )
    return FileResponse(
        file_path.open("rb"),
        content_type="text/html"
    )


urlpatterns = [
    path(
        'googlebf6b22f221e979ef.html',
        google_site_verification,
        name='google-site-verification'
    ),

    path('', TemplateView.as_view(
        template_name='users/tanitim.html'
    ), name='landing'),

    path('dashboard/', include('dashboard.urls')),

    path('api/auth/', include('users.urls')),
    path('api/', include('todos.urls')),

    path('login/', TemplateView.as_view(
        template_name='users/login.html'
    ), name='login'),

    path('register/', TemplateView.as_view(
        template_name='users/register.html'
    ), name='register'),

    path('app/', TemplateView.as_view(
        template_name='users/home.html'
    ), name='home'),
]
