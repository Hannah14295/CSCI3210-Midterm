"""Race rules shared by API actions and real-time connections."""
from functools import partial
from decimal import Decimal
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError

from .models import Race, RaceParticipant
from .events import broadcast, broadcast_race_state
from .typing import typing_metrics, text_difference, calculate_wpm


class RaceConflict(APIException):
    status_code = 409
    default_detail = "This race is no longer waiting."


@transaction.atomic
def create_race(*, host, paragraph):
    race = Race.objects.create(host=host, paragraph=paragraph)
    # Creating a lobby also enters its host as a competitor.
    RaceParticipant.objects.create(race=race, player=host)
    return race


@transaction.atomic
def join_race(*, race_id, player):
    race = get_object_or_404(Race.objects.select_for_update(), pk=race_id)
    if race.status != Race.Status.WAITING:
        raise RaceConflict("You can only join a waiting race.")
    participant, created = RaceParticipant.objects.get_or_create(race=race, player=player)
    if created:
        transaction.on_commit(partial(broadcast_race_state, race.pk))
    return participant, created


@transaction.atomic
def start_race(*, race_id, player):
    race = get_object_or_404(Race.objects.select_for_update(), pk=race_id)
    if race.host_id != player.pk:
        raise PermissionDenied("Only the host can start this race.")
    if race.status != Race.Status.WAITING:
        raise RaceConflict("This race has already started or finished.")
    race.status = Race.Status.RUNNING
    race.started_at = timezone.now()
    race.race_text = race.paragraph.text
    race.save(update_fields=["status", "started_at", "race_text"])
    transaction.on_commit(partial(broadcast_race_state, race.pk))
    return race


@transaction.atomic
def update_typing(*, race_id, player_id, text):
    race = get_object_or_404(Race.objects.select_for_update(), pk=race_id)
    if race.status != Race.Status.RUNNING or race.started_at is None or not race.race_text:
        raise RaceConflict("Start a waiting race through the API before typing.")
    if not isinstance(text, str) or len(text) > min(2000, len(race.race_text)):
        raise ValidationError("Typed text must be a string no longer than the race paragraph.")
    participant = RaceParticipant.objects.select_related("player").filter(
        race=race, player_id=player_id, player__is_active=True,
    ).first()
    if participant is None:
        raise PermissionDenied("Join this race before typing.")
    if participant.finished_at is not None:
        raise RaceConflict("Your result is already saved. Join a new race to try again.")
    if not text.startswith(participant.typed_text):
        raise ValidationError("Type forward only. Previously entered characters cannot be removed or changed.")
    now = timezone.now()
    elapsed = Decimal(str((now - race.started_at).total_seconds()))
    if elapsed <= 0:
        raise RaceConflict("The race start time must be in the past.")
    metrics = typing_metrics(race.race_text, text)
    difference = text_difference(participant.typed_text, text)
    participant.typed_text = text
    participant.revision += 1
    current_wpm = calculate_wpm(metrics["correct_characters"], elapsed)
    if metrics["complete"]:
        participant.finished_at = now
        participant.elapsed_seconds = elapsed
        participant.wpm = current_wpm
    participant.save(update_fields=["typed_text", "revision", "finished_at", "elapsed_seconds", "wpm"])
    payload = {
        "type": "progress.updated",
        "race_id": race.pk,
        "player": {"id": player_id, "username": participant.player.username},
        "revision": participant.revision,
        "difference": difference,
        **metrics,
        "wpm": float(current_wpm),
        "finished_at": participant.finished_at.isoformat() if participant.finished_at else None,
        "elapsed_seconds": float(elapsed),
    }
    transaction.on_commit(partial(broadcast, race.pk, payload))
    if participant.finished_at is not None:
        race.status = Race.Status.FINISHED
        race.save(update_fields=["status"])
        transaction.on_commit(partial(broadcast_race_state, race.pk))
    return payload
