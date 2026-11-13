
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth import login as django_login
User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'nick',
            'is_staff',
            'created_at',
            'updated_at'
        )

        read_only_fields = (
            'id',
            'is_staff',
            'created_at',
            'updated_at'
        )


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    nick = serializers.CharField(required=False, allow_blank=True, max_length=50)

    class Meta:
        model = User
        fields = ('username', 'nick', 'password')

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            nick=validated_data.get('nick', '')
        )
        return user



class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        from django.contrib.auth import authenticate

        user = authenticate(
            username=attrs.get('username'),
            password=attrs.get('password')
        )

        if not user:
            raise serializers.ValidationError(
                'Geçersiz kullanıcı adı veya şifre.'
            )

        if not user.is_active:
            raise serializers.ValidationError(
                'Bu hesap devre dışı bırakılmış.'
            )

        # Django oturumunu da başlat
        request = self.context.get('request')
        if request:
            django_login(request, user)

        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)

        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        }



class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)

    def validate_old_password(self, value):
        user = self.context['request'].user

        if not user.check_password(value):
            raise serializers.ValidationError(
                "Mevcut şifreniz yanlış."
            )

        return value

    def validate(self, data):
        if data['old_password'] == data['new_password']:
            raise serializers.ValidationError({
                "new_password": "Yeni şifre eskisinden farklı olmalıdır."
            })

        return data
