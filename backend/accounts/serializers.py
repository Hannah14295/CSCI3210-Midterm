from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Public account fields; never return passwords or password hashes."""

    class Meta:
        model = User
        fields = ["id", "username"]
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, trim_whitespace=False, max_length=128,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = ["username", "password"]

    def validate(self, attrs):
        # Including username lets Django check for overly similar passwords.
        candidate = User(username=attrs["username"])
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": error.messages})
        return attrs

    def create(self, validated_data):
        # create_user hashes the password and creates a regular, non-staff user.
        return User.objects.create_user(**validated_data)
