from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Race
from .serializers import RaceSerializer


def race_snapshot(race_id):
    race = Race.objects.select_related("host", "paragraph").prefetch_related(
        "participants__player"
    ).get(pk=race_id)
    return RaceSerializer(race).data


def broadcast(race_id, payload):
    async_to_sync(get_channel_layer().group_send)(
        f"race.{race_id}", {"type": "race.message", "payload": payload},
    )


def broadcast_race_state(race_id):
    broadcast(race_id, {"type": "race.updated", "race": race_snapshot(race_id)})
