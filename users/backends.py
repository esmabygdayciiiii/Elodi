from django.contrib.auth.backends import ModelBackend


class VerifiedUserBackend(ModelBackend):
    """E-postasını doğrulamamış kullanıcıların giriş yapmasını engeller."""

    def user_can_authenticate(self, user):
        return super().user_can_authenticate(user) and user.is_verified