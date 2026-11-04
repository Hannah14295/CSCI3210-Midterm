from rest_framework import serializers
from django.utils import timezone

from accounts.serializers import UserSerializer

from .models import Paragraph, Race, RaceParticipant
from .typing import typing_metrics, calculate_wpm


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
        race = participant.race
        metrics = typing_metrics(race.race_text, participant.typed_text)
        end = participant.finished_at or timezone.now()
        elapsed = (end - participant.typing_started_at).total_seconds() if participant.typing_started_at else 0
        metrics["wpm"] = float(
            participant.wpm if participant.wpm is not None
            else calculate_wpm(metrics["correct_characters"], elapsed)
        )
        return metrics

    class Meta:
        model = RaceParticipant
        fields = ["id", "player", "joined_at", "revision", "typing_started_at", "metrics", "finished_at", "elapsed_seconds", "wpm", "accuracy"]
        read_only_fields = fields


class RaceSerializer(serializers.ModelSerializer):
    host = UserSerializer(read_only=True)
    participants = RaceParticipantSerializer(many=True, read_only=True)
    paragraph_text = serializers.SerializerMethodField()
    server_time = serializers.SerializerMethodField()

    def get_server_time(self, race):
        return timezone.now().isoformat()

    def get_paragraph_text(self, race):
        return race.race_text or race.paragraph.text

    class Meta:
        model = Race
        fields = ["id", "paragraph", "paragraph_text", "host", "status", "created_at", "started_at", "server_time", "participants"]
        read_only_fields = ["id", "paragraph_text", "host", "status", "created_at", "started_at", "server_time", "participants"]


class LeaderboardSerializer(serializers.ModelSerializer):
    rank = serializers.IntegerField(read_only=True)
    player = UserSerializer(read_only=True)

    class Meta:
        model = RaceParticipant
        fields = ["rank", "id", "race", "player", "wpm", "accuracy", "elapsed_seconds", "finished_at"]
        read_only_fields = fields
