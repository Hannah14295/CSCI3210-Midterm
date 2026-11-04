from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import Paragraph, Race, RaceParticipant


class RaceAPITests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.host = User.objects.create_user(username="host")
        self.other = User.objects.create_user(username="other")
        self.paragraph = Paragraph.objects.create(title="Practice", text="A passage for our practice race.")
        self.race = Race.objects.create(host=self.host, paragraph=self.paragraph)

    def authenticate(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_endpoints_require_authentication(self):
        self.assertEqual(self.client.get(reverse("race-list")).status_code, 401)
        for url, body in [
            (reverse("race-list"), {"paragraph": self.paragraph.pk}),
            (reverse("race-join", args=[self.race.pk]), {}),
            (reverse("race-start", args=[self.race.pk]), {}),
        ]:
            self.assertEqual(self.client.post(url, body).status_code, 401)

    def test_create_uses_authenticated_host_and_enters_them(self):
        self.authenticate(self.host)
        response = self.client.post(reverse("race-list"), {
            "paragraph": self.paragraph.pk, "host": self.other.pk,
            "status": "finished", "started_at": "2020-01-01T00:00:00Z",
        })
        self.assertEqual(response.status_code, 201)
        race = Race.objects.get(pk=response.data["id"])
        self.assertEqual(race.host, self.host)
        self.assertEqual(race.status, Race.Status.WAITING)
        self.assertIsNone(race.started_at)
        self.assertEqual(race.participants.get().player, self.host)

    def test_invalid_paragraph_does_not_create_race(self):
        self.authenticate(self.host)
        for body in [{}, {"paragraph": 99999}, {"paragraph": "invalid"}]:
            self.assertEqual(self.client.post(reverse("race-list"), body).status_code, 400)
        self.assertEqual(Race.objects.count(), 1)

    def test_join_uses_identity_and_repeated_join_has_one_entry(self):
        self.authenticate(self.other)
        url = reverse("race-join", args=[self.race.pk])
        response = self.client.post(url, {"player": self.host.pk})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["player"]["id"], self.other.pk)
        self.assertEqual(self.client.post(url).status_code, 200)
        self.assertEqual(self.race.participants.count(), 1)

    def test_only_host_can_start_and_start_time_cannot_be_reset(self):
        url = reverse("race-start", args=[self.race.pk])
        self.authenticate(self.other)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.race.refresh_from_db()
        self.assertIsNone(self.race.started_at)
        self.authenticate(self.host)
        self.assertEqual(self.client.post(url).status_code, 200)
        self.race.refresh_from_db()
        start = self.race.started_at
        self.assertIsNotNone(start)
        self.assertEqual(self.race.status, Race.Status.RUNNING)
        self.assertEqual(self.client.post(url).status_code, 409)
        self.race.refresh_from_db()
        self.assertEqual(self.race.started_at, start)

    def test_cannot_join_or_start_finished_race_or_join_running_race(self):
        self.authenticate(self.host)
        for race_status in [Race.Status.RUNNING, Race.Status.FINISHED]:
            self.race.status = race_status
            self.race.save()
            self.assertEqual(self.client.post(reverse("race-join", args=[self.race.pk])).status_code, 409)
            self.assertEqual(self.client.post(reverse("race-start", args=[self.race.pk])).status_code, 409)
        self.assertFalse(RaceParticipant.objects.exists())

    def test_missing_races_return_404(self):
        self.authenticate(self.host)
        self.assertEqual(self.client.get(reverse("race-detail", args=[99999])).status_code, 404)
        for action in ["race-join", "race-start"]:
            self.assertEqual(self.client.post(reverse(action, args=[99999])).status_code, 404)

    def test_list_and_detail_expose_participants_without_account_secrets(self):
        RaceParticipant.objects.create(race=self.race, player=self.other)
        self.authenticate(self.host)
        detail = self.client.get(reverse("race-detail", args=[self.race.pk]))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["participants"][0]["player"], {"id": self.other.pk, "username": "other"})
        self.assertEqual(set(detail.data["host"]), {"id", "username"})
        self.assertEqual(self.client.get(reverse("race-list")).data["count"], 1)

    def test_arbitrary_edit_and_delete_are_not_exposed(self):
        self.authenticate(self.host)
        url = reverse("race-detail", args=[self.race.pk])
        self.assertEqual(self.client.patch(url, {"status": "running"}).status_code, 405)
        self.assertEqual(self.client.delete(url).status_code, 405)
