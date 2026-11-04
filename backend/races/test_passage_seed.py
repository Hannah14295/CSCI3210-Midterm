from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.db import connection
from django.test import TestCase
from django.urls import reverse

from .models import Paragraph


class FablePassageSeedTests(TestCase):
    def setUp(self):
        Paragraph.objects.all().delete()
        self.migration = import_module("races.migrations.0008_add_fable_passages")

    def seed(self):
        self.migration.add_fables(apps, SimpleNamespace(connection=connection))

    def test_fables_are_valid_and_available_to_the_public_dropdown_api(self):
        self.seed()
        passages = list(Paragraph.objects.all())
        self.assertEqual(len(passages), 5)
        for passage in passages:
            passage.full_clean()
        response = self.client.get(reverse("paragraph-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 5)
        self.assertIn("The Tortoise and the Hare", [entry["title"] for entry in response.json()["results"]])
        self.assertIn("The Lion and the Mouse", [entry["title"] for entry in response.json()["results"]])

    def test_seed_preserves_edits_and_other_passages_without_duplicates(self):
        edited = Paragraph.objects.create(title="The Lion and the Mouse", text="My own edited version of this fable.")
        custom = Paragraph.objects.create(title="Custom passage", text="Keep this unrelated passage in the library.")
        self.seed()
        self.seed()
        self.assertEqual(Paragraph.objects.count(), 6)
        edited.refresh_from_db()
        self.assertEqual(edited.text, "My own edited version of this fable.")
        self.assertTrue(Paragraph.objects.filter(pk=custom.pk).exists())
