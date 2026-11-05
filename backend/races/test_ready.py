from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from .models import Paragraph, Race, RaceParticipant


class ReadyTests(APITestCase):
    def setUp(self):
        self.host = get_user_model().objects.create_user(username="readyhost")
        self.guest = get_user_model().objects.create_user(username="readyguest")
        self.race = Race.objects.create(host=self.host, paragraph=Paragraph.objects.first())
        self.first = RaceParticipant.objects.create(race=self.race, player=self.host)
        self.second = RaceParticipant.objects.create(race=self.race, player=self.guest)
        self.url = reverse("race-ready", args=[self.race.pk])

    def test_all_players_must_be_ready_and_only_the_host_starts(self):
        self.client.force_authenticate(self.host)
        start = reverse("race-start", args=[self.race.pk])
        self.assertEqual(self.client.post(start).status_code, 409)
        self.assertEqual(self.client.post(self.url, {"ready": True}, format="json").status_code, 200)
        self.assertEqual(self.client.post(start).status_code, 409)
        self.client.force_authenticate(self.guest)
        self.client.post(self.url, {"ready": True}, format="json")
        self.assertEqual(self.client.post(start).status_code, 403)
        self.client.force_authenticate(self.host)
        self.assertEqual(self.client.post(start).status_code, 200)
        self.assertEqual(self.client.post(self.url, {"ready": False}, format="json").status_code, 409)

    def test_readiness_can_be_revoked_but_cannot_change_another_player(self):
        self.client.force_authenticate(self.host)
        self.client.post(self.url, {"ready": True, "player": self.guest.pk}, format="json")
        self.first.refresh_from_db(); self.second.refresh_from_db()
        self.assertTrue(self.first.is_ready)
        self.assertFalse(self.second.is_ready)
        self.client.post(self.url, {"ready": False}, format="json")
        self.first.refresh_from_db()
        self.assertFalse(self.first.is_ready)
        self.assertEqual(self.client.post(self.url, {"ready": "false"}, format="json").status_code, 400)

    def test_outsiders_cannot_mark_ready(self):
        outsider = get_user_model().objects.create_user(username="readyoutsider")
        self.client.force_authenticate(outsider)
        self.assertEqual(self.client.post(self.url, {"ready": True}, format="json").status_code, 403)
