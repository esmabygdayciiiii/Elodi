from django.conf import settings
from django.db import models
from django.utils import timezone


class Pomodoro(models.Model):
  user = models.ForeignKey(
      settings.AUTH_USER_MODEL,
      on_delete=models.CASCADE,
      related_name='pomodoros',
  )
  # O gün içinde toplam kaç dakika odaklanıldı
  total_minutes = models.PositiveIntegerField(default=0)
  # O gün kaç adet Pomodoro seansı tamamlandı (örneğin 25 dk = 1 seans)
  completed_sessions = models.PositiveIntegerField(default=0)
  # Hangi güne ait kayıt olduğu (24 saatlik gün kontrolünü bu alan sağlar!)
  date = models.DateField(default=timezone.localdate)
  updated_at = models.DateTimeField(auto_now=True)

  class Meta:
    # Aynı kullanıcı için aynı tarihte sadece tek bir günlük özet satırı olsun
    unique_together = ('user', 'date')
    ordering = ['-date']

  def __str__(self):
    return f'{self.user} - {self.date} ({self.total_minutes} dk)'

  @property
  def formatted_duration(self):
    """Ekranda '2 sa 15 dk' gibi şık göstermek için yardımcı özellik"""
    hours = self.total_minutes // 60
    minutes = self.total_minutes % 60
    if hours > 0:
      return f'{hours} sa {minutes} dk'
    return f'{minutes} dk'