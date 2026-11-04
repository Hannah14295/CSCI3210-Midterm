from rest_framework import serializers

from accounts.serializers import UserSerializer

from .models import Paragraph, Race, RaceParticipant
from .typing import typing_metrics


class ParagraphSerializer(serializers.ModelSerializer):
    """Choose which model fields the API exposes as JSON."""

    class Meta:
        model = Paragraph
        fields = ["id", "title", "text"]
        read_only_fields = fields


class RaceParticipantSerializer(serializers.ModelSerializer):
    player = UserSerializer(read_only=True)
    metrics = serializers.SerializerMethodField()

    def get_metrics(self, participant):
        return typing_metrics(participant.race.race_text, participant.typed_text)

    class Meta:
        model = RaceParticipant
        fields = ["id", "player", "joined_at", "revision", "metrics"]
        read_only_fields = fields


class RaceSerializer(serializers.ModelSerializer):
    host = UserSerializer(read_only=True)
    participants = RaceParticipantSerializer(many=True, read_only=True)
    paragraph_text = serializers.SerializerMethodField()

    def get_paragraph_text(self, race):
        return race.race_text or race.paragraph.text

    class Meta:
        model = Race
        fields = ["id", "paragraph", "paragraph_text", "host", "status", "created_at", "started_at", "participants"]
        read_only_fields = ["id", "paragraph_text", "host", "status", "created_at", "started_at", "participants"]
