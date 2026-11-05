"""Race rules shared by API actions and real-time connections."""
from functools import partial
from decimal import Decimal
from datetime import timedelta
from django.conf import settings
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
def create_rematch(*, race_id, player):
    previous = get_object_or_404(Race.objects.select_for_update(), pk=race_id)
    if previous.host_id != player.pk:
        raise PermissionDenied("Only the host can create the next race.")
    if previous.status != Race.Status.FINISHED:
        raise RaceConflict("Everyone must finish before racing again.")
    if previous.next_race_id:
        return previous.next_race, False
    race = Race.objects.create(
        host_id=previous.host_id, paragraph_id=previous.paragraph_id,
        race_text=previous.race_text,
    )
    players = set(previous.participants.filter(player__is_active=True).values_list("player_id", flat=True))
    players.add(previous.host_id)
    RaceParticipant.objects.bulk_create([
        RaceParticipant(race=race, player_id=player_id) for player_id in sorted(players)
    ])
    previous.next_race = race
    previous.save(update_fields=["next_race"])
    transaction.on_commit(partial(broadcast_race_state, previous.pk))
    return race, True


@transaction.atomic
def set_ready(*, race_id, player, ready):
    race = get_object_or_404(Race.objects.select_for_update(), pk=race_id)
    if race.status != Race.Status.WAITING:
        raise RaceConflict("Readiness can only change in a waiting room.")
    participant = race.participants.filter(player=player).first()
    if participant is None:
        raise PermissionDenied("Join this race before marking yourself ready.")
    participant.is_ready = ready
    participant.save(update_fields=["is_ready"])
    transaction.on_commit(partial(broadcast_race_state, race.pk))
    return race


@transaction.atomic
def start_race(*, race_id, player):
    race = get_object_or_404(Race.objects.select_for_update(), pk=race_id)
    if race.host_id != player.pk:
        raise PermissionDenied("Only the host can start this race.")
    if race.status != Race.Status.WAITING:
        raise RaceConflict("This race has already started or finished.")
    if not race.participants.exists() or race.participants.filter(is_ready=False).exists():
        raise RaceConflict("Every racer must be ready before starting.")
    race.status = Race.Status.RUNNING
    race.started_at = timezone.now() + timedelta(seconds=settings.RACE_COUNTDOWN_SECONDS)
    race.race_text = race.race_text or race.paragraph.text
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
    if now < race.started_at:
        raise RaceConflict("Wait for the countdown to reach Go before typing.")
    if text and participant.typing_started_at is None:
        participant.typing_started_at = now
    elapsed = Decimal(str((now - participant.typing_started_at).total_seconds())) if participant.typing_started_at else Decimal(0)
    if elapsed < 0:
        raise RaceConflict("The player's typing start time must be in the past.")
    metrics = typing_metrics(race.race_text, text)
    # A whole passage submitted in its very first packet still needs a positive duration.
    if metrics["complete"]:
        elapsed = max(elapsed, Decimal("0.001"))
    difference = text_difference(participant.typed_text, text)
    participant.typed_text = text
    participant.revision += 1
    current_wpm = calculate_wpm(metrics["correct_characters"], elapsed)
    if metrics["complete"]:
        participant.finished_at = now
        participant.elapsed_seconds = elapsed
        participant.wpm = current_wpm
        participant.accuracy = Decimal(str(metrics["accuracy"]))
    participant.save(update_fields=["typed_text", "revision", "typing_started_at", "finished_at", "elapsed_seconds", "wpm", "accuracy"])
    payload = {
        "type": "progress.updated",
        "race_id": race.pk,
        "player": {"id": player_id, "username": participant.player.username},
        "revision": participant.revision,
        "typing_started_at": participant.typing_started_at.isoformat() if participant.typing_started_at else None,
        "difference": difference,
        **metrics,
        "wpm": float(current_wpm),
        "finished_at": participant.finished_at.isoformat() if participant.finished_at else None,
        "elapsed_seconds": float(elapsed),
    }
    transaction.on_commit(partial(broadcast, race.pk, payload))
    if participant.finished_at is not None:
        # The race row lock serializes finishes so only the last player ends it.
        if not RaceParticipant.objects.filter(race=race, finished_at__isnull=True).exists():
            race.status = Race.Status.FINISHED
            race.save(update_fields=["status"])
        transaction.on_commit(partial(broadcast_race_state, race.pk))
    return payload
