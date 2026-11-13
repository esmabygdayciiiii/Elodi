import logging
from urllib.parse import urlencode

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

logger = logging.getLogger(__name__)

SALT = "users.email-verification"


def make_verification_token(user):
    # E-posta da imzaya dahil: e-posta değişirse eski token geçersiz olur.
    return signing.dumps({"uid": str(user.pk), "email": user.email}, salt=SALT)


def read_verification_token(token):
    """Geçerliyse (uid, email) döndürür; değilse signing hatası fırlatır."""
    max_age = getattr(settings, "EMAIL_VERIFICATION_MAX_AGE", 60 * 60 * 24)
    data = signing.loads(token, salt=SALT, max_age=max_age)
    return data["uid"], data["email"]


def send_verification_email(user, request):
    """Doğrulama e-postasını gönderir. Başarılıysa True döner."""
    path = reverse("users:verify-email")
    query = urlencode({"token": make_verification_token(user)})
    link = request.build_absolute_uri(f"{path}?{query}")

    try:
        send_mail(
            subject="E-posta adresini doğrula",
            message=(
                f"Merhaba {user.name},\n\n"
                f"Hesabını etkinleştirmek için bu bağlantıya tıkla:\n{link}\n\n"
                "Bağlantı 24 saat geçerlidir. Bu hesabı sen oluşturmadıysan "
                "bu e-postayı yok sayabilirsin."
            ),
            from_email=None,  # settings.DEFAULT_FROM_EMAIL
            recipient_list=[user.email],
        )
    except Exception:
        logger.exception("Doğrulama e-postası gönderilemedi: %s", user.pk)
        return False
    return True


def send_password_reset_email(user, request):
    """Şifre sıfırlama e-postasını gönderir. Başarılıysa True döner.

    Token Django'nun kendi üretecinden gelir: kullanıcının mevcut şifresine bağlıdır,
    bu yüzden şifre değişince eski bağlantı otomatik geçersiz olur (tek kullanımlık).
    Süre: settings.PASSWORD_RESET_TIMEOUT (saniye).
    """
    uid = urlsafe_base64_encode(force_bytes(str(user.pk)))
    token = default_token_generator.make_token(user)
    query = urlencode({"uid": uid, "token": token})
    link = request.build_absolute_uri(f"/reset-password/?{query}")

    try:
        send_mail(
            subject="Şifreni sıfırla",
            message=(
                f"Merhaba {user.name},\n\n"
                f"Şifreni sıfırlamak için bu bağlantıya tıkla:\n{link}\n\n"
                "Bağlantı 1 saat geçerlidir ve yalnızca bir kez kullanılabilir. "
                "Bu isteği sen yapmadıysan bu e-postayı yok sayabilirsin, şifren değişmez."
            ),
            from_email=None,
            recipient_list=[user.email],
        )
    except Exception:
        logger.exception("Şifre sıfırlama e-postası gönderilemedi: %s", user.pk)
        return False
    return True