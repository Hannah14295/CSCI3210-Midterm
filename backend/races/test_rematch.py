from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import Paragraph, Race, RaceParticipant


class RematchTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.host = User.objects.create_user(username="rematchhost")
        self.guest = User.objects.create_user(username="rematchguest")
        self.outsider = User.objects.create_user(username="rematchoutsider")
        self.paragraph = Paragraph.objects.create(title="Rematch", text="A passage for another friendly typing race.")
        self.race = Race.objects.create(host=self.host, paragraph=self.paragraph, race_text=self.paragraph.text,
                                        status=Race.Status.FINISHED, started_at=timezone.now() - timedelta(seconds=60))
        for player in (self.host, self.guest):
            RaceParticipant.objects.create(race=self.race, player=player, typed_text=self.paragraph.text,
                                            finished_at=timezone.now(), elapsed_seconds=60, wpm=50, accuracy=100)
        self.url = reverse("race-rematch", args=[self.race.pk])

    def test_only_the_authenticated_host_can_create_a_rematch(self):
        self.assertEqual(self.client.post(self.url).status_code, 401)
        for player in (self.guest, self.outsider):
            self.client.force_authenticate(player)
            self.assertEqual(self.client.post(self.url).status_code, 403)
        self.assertEqual(Race.objects.count(), 1)

    def test_race_again_creates_one_fresh_room_and_preserves_the_old_results(self):
        self.client.force_authenticate(self.host)
        response = self.client.post(self.url, {"host": self.outsider.pk, "wpm": 9999})
        self.assertEqual(response.status_code, 201)
        race = Race.objects.get(pk=response.data["id"])
        self.assertEqual(race.host_id, self.host.pk)
        self.assertEqual(race.paragraph_id, self.paragraph.pk)
        self.assertEqual(race.status, Race.Status.WAITING)
        self.assertIsNone(race.started_at)
        self.assertEqual(set(race.participants.values_list("player_id", flat=True)), {self.host.pk, self.guest.pk})
        for participant in race.participants.all():
            self.assertEqual(participant.typed_text, "")
            self.assertEqual(participant.revision, 0)
            self.assertIsNone(participant.typing_started_at)
            self.assertIsNone(participant.finished_at)
            self.assertIsNone(participant.wpm)
            self.assertIsNone(participant.accuracy)
        self.race.refresh_from_db()
        self.assertEqual(self.race.next_race_id, race.pk)
        self.assertEqual(self.race.status, Race.Status.FINISHED)
        self.assertEqual(self.race.participants.filter(wpm=50, accuracy=100).count(), 2)
        repeated = self.client.post(self.url)
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(repeated.data["id"], race.pk)
        self.assertEqual(Race.objects.count(), 2)

    def test_cannot_rematch_before_everyone_has_finished(self):
        self.client.force_authenticate(self.host)
        for status in (Race.Status.WAITING, Race.Status.RUNNING):
            self.race.status = status
            self.race.save(update_fields=["status"])
            self.assertEqual(self.client.post(self.url).status_code, 409)
        self.assertEqual(Race.objects.count(), 1)

    def test_rematch_reuses_the_frozen_passage_even_if_admin_edits_the_original(self):
        frozen = self.race.race_text
        self.paragraph.text = "An edited passage that should not replace the rematch text."
        self.paragraph.save()
        self.client.force_authenticate(self.host)
        response = self.client.post(self.url)
        self.assertEqual(response.data["paragraph_text"], frozen)
        RaceParticipant.objects.filter(race_id=response.data["id"]).update(is_ready=True)
        started = self.client.post(reverse("race-start", args=[response.data["id"]]))
        self.assertEqual(started.status_code, 200)
        self.assertEqual(started.data["paragraph_text"], frozen)

    def test_inactive_accounts_are_not_entered_into_a_new_race(self):
        self.guest.is_active = False
        self.guest.save(update_fields=["is_active"])
        self.client.force_authenticate(self.host)
        response = self.client.post(self.url)
        self.assertEqual(len(response.data["participants"]), 1)
