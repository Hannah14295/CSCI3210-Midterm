from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import Paragraph, Race


class ParagraphAPITests(APITestCase):
    def setUp(self):
        self.paragraph = Paragraph.objects.create(
            title="Practice", text="Steady practice builds speed and accuracy."
        )

    def test_anonymous_player_can_read_saved_text(self):
        response = self.client.get(reverse("paragraph-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["text"], self.paragraph.text)

    def test_detail_and_missing_paragraph(self):
        response = self.client.get(reverse("paragraph-detail", args=[self.paragraph.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.paragraph.pk)
        self.assertEqual(
            self.client.get(reverse("paragraph-detail", args=[99999])).status_code,
            404,
        )

    def test_api_does_not_allow_players_to_change_passages(self):
        self.assertEqual(
            self.client.post(reverse("paragraph-list"), {"title": "Changed"}).status_code,
            405,
        )
        url = reverse("paragraph-detail", args=[self.paragraph.pk])
        self.assertEqual(self.client.patch(url, {"text": "Changed"}).status_code, 405)
        self.assertEqual(self.client.delete(url).status_code, 405)
        self.paragraph.refresh_from_db()
        self.assertEqual(self.paragraph.title, "Practice")


class ParagraphAdminTests(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_superuser(
            username="testadmin", email="admin@example.com", password="test-only-password"
        )

    def test_staff_can_add_paragraph_and_read_it_through_api(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("admin:races_paragraph_add"),
            {"title": "From admin", "text": "This passage was saved through the admin form.", "_save": "Save"},
        )
        self.assertEqual(response.status_code, 302)
        self.client.logout()
        response = self.client.get(reverse("paragraph-list"))
        self.assertEqual(response.json()["results"][0]["title"], "From admin")

    def test_admin_rejects_short_paragraph(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("admin:races_paragraph_add"), {"title": "Too short", "text": "Hi"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text", response.context["adminform"].form.errors)
        self.assertFalse(Paragraph.objects.exists())


class RaceTests(TestCase):
    def setUp(self):
        self.host = get_user_model().objects.create_superuser(
            username="racehost", email="host@example.com", password="test-only-password"
        )
        self.paragraph = Paragraph.objects.create(
            title="Practice", text="Steady practice builds speed and accuracy."
        )

    def test_race_defaults_and_relationships(self):
        race = Race.objects.create(host=self.host, paragraph=self.paragraph)
        race.refresh_from_db()
        self.assertEqual(race.status, Race.Status.WAITING)
        self.assertEqual(self.host.hosted_races.get(), race)
        self.assertEqual(self.paragraph.races.get(), race)
        with self.assertRaises(ProtectedError):
            self.paragraph.delete()
        with self.assertRaises(ProtectedError):
            self.host.delete()

    def test_model_validation_rejects_unknown_status(self):
        race = Race(host=self.host, paragraph=self.paragraph, status="unknown")
        with self.assertRaises(ValidationError):
            race.full_clean()

    def test_admin_can_create_a_waiting_race(self):
        self.client.force_login(self.host)
        response = self.client.post(
            reverse("admin:races_race_add"),
            {"host": self.host.pk, "paragraph": self.paragraph.pk, "status": "waiting", "_save": "Save"},
        )
        self.assertEqual(response.status_code, 302)
        race = Race.objects.get()
        self.assertEqual(race.host, self.host)
        self.assertEqual(race.paragraph, self.paragraph)
        self.assertEqual(race.status, Race.Status.WAITING)
