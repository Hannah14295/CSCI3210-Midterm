"""Race rules shared by API actions and, later, real-time connections."""
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import APIException, PermissionDenied

from .models import Race, RaceParticipant


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
    race.save(update_fields=["status", "started_at"])
    return race
