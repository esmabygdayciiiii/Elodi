
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
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
