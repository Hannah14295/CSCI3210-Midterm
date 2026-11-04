from rest_framework import serializers

from accounts.serializers import UserSerializer

from .models import Paragraph, Race, RaceParticipant


class ParagraphSerializer(serializers.ModelSerializer):
    """Choose which model fields the API exposes as JSON."""

    class Meta:
        model = Paragraph
        fields = ["id", "title", "text"]
        read_only_fields = fields


class RaceParticipantSerializer(serializers.ModelSerializer):
    player = UserSerializer(read_only=True)

    class Meta:
        model = RaceParticipant
        fields = ["id", "player", "joined_at"]
        read_only_fields = fields


class RaceSerializer(serializers.ModelSerializer):
    host = UserSerializer(read_only=True)
    participants = RaceParticipantSerializer(many=True, read_only=True)

    class Meta:
        model = Race
        fields = ["id", "paragraph", "host", "status", "created_at", "started_at", "participants"]
        read_only_fields = ["id", "host", "status", "created_at", "started_at", "participants"]
