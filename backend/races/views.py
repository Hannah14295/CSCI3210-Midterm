from rest_framework import mixins, serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet
from django.db.models import F, Window
from django.db.models.functions import RowNumber

from .models import Paragraph, Race, RaceParticipant
from .serializers import ParagraphSerializer, RaceSerializer, RaceParticipantSerializer, LeaderboardSerializer
from . import services


class ParagraphViewSet(ReadOnlyModelViewSet):
    """Anyone can read practice text; only admin users can edit it via admin."""

    queryset = Paragraph.objects.all()
    serializer_class = ParagraphSerializer
    permission_classes = [AllowAny]


class RaceViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
):
    serializer_class = RaceSerializer
    permission_classes = [IsAuthenticated]
    queryset = Race.objects.select_related("host", "paragraph").prefetch_related("participants__player")

    def get_serializer_class(self):
        if self.action in ("join", "start"):
            return serializers.Serializer  # These actions take no body fields.
        return super().get_serializer_class()

    def perform_create(self, serializer):
        # Identity comes from authentication, never from a submitted host ID.
        serializer.instance = services.create_race(
            host=self.request.user, paragraph=serializer.validated_data["paragraph"]
        )

    @action(detail=True, methods=["post"])
    def join(self, request, pk=None):
        participant, created = services.join_race(race_id=pk, player=request.user)
        return Response(
            RaceParticipantSerializer(participant).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        race = services.start_race(race_id=pk, player=request.user)
        return Response(RaceSerializer(race).data)


class LeaderboardViewSet(mixins.ListModelMixin, GenericViewSet):
    """Historical completed runs, fastest first; ties use finish time then ID."""

    permission_classes = [AllowAny]
    serializer_class = LeaderboardSerializer
    queryset = RaceParticipant.objects.filter(
        finished_at__isnull=False, wpm__isnull=False, elapsed_seconds__gt=0,
    ).select_related("player").annotate(
        rank=Window(
            expression=RowNumber(),
            order_by=[F("wpm").desc(), F("finished_at").asc(), F("id").asc()],
        ),
    ).order_by("-wpm", "finished_at", "id")
