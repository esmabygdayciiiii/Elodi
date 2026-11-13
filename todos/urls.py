from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, TodoViewSet, save_pomodoro

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'todos', TodoViewSet, basename='todo')

urlpatterns = [
    path('', include(router.urls)),
    path('pomodoro/save/', save_pomodoro, name='save-pomodoro'),
]