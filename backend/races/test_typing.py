from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import Paragraph, Race, RaceParticipant
from .services import RaceConflict, start_race, update_typing
from .typing import typing_metrics, text_difference


class TextComparisonTests(SimpleTestCase):
    def test_mistake_stops_progress_but_accuracy_counts_all_matches(self):
        metrics = typing_metrics("hello", "hexlo")
        self.assertEqual(metrics["correct_prefix"], 2)
        self.assertEqual(metrics["correct_characters"], 4)
        self.assertEqual(metrics["progress"], 40)
        self.assertEqual(metrics["accuracy"], 80)
        self.assertFalse(metrics["complete"])

    def test_empty_and_complete_buffers(self):
        self.assertEqual(typing_metrics("hello", "")["progress"], 0)
        self.assertEqual(typing_metrics("hello", "")["accuracy"], 100)
        metrics = typing_metrics("hello", "hello")
        self.assertEqual(metrics["progress"], 100)
        self.assertTrue(metrics["complete"])
        self.assertFalse(typing_metrics("", "")["complete"])

    def test_difference_reconstructs_corrections_backspaces_and_unicode(self):
        for before, after in [("", "abc"), ("hexlo", "hello"), ("hello", "hel"), ("hel", ""), ("café", "café!"), ("same", "same")]:
            diff = text_difference(before, after)
            rebuilt = before[:diff["start"]] + diff["insert"] + before[diff["start"] + diff["delete_count"]:]
            self.assertEqual(rebuilt, after)


class TypingServiceTests(TestCase):
    def setUp(self):
        self.player = get_user_model().objects.create_user(username="typist")
        self.paragraph = Paragraph.objects.create(title="Practice", text="hello world, practice today")
        self.race = Race.objects.create(host=self.player, paragraph=self.paragraph)
        self.entry = RaceParticipant.objects.create(race=self.race, player=self.player)

    def update(self, text):
        return update_typing(race_id=self.race.pk, player_id=self.player.pk, text=text)

    def test_waiting_and_finished_races_reject_typing(self):
        with self.assertRaises(RaceConflict):
            self.update("h")
        self.race.status = Race.Status.FINISHED
        self.race.save()
        with self.assertRaises(RaceConflict):
            self.update("h")
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.revision, 0)

    def test_start_freezes_text_and_typing_tracks_corrections(self):
        start_race(race_id=self.race.pk, player=self.player)
        original = self.paragraph.text
        self.paragraph.text = "An entirely different passage"
        self.paragraph.save()
        first = self.update("hexlo")
        self.assertEqual(first["correct_prefix"], 2)
        self.assertEqual(first["accuracy"], 80)
        corrected = self.update("hello")
        self.assertEqual(corrected["correct_prefix"], 5)
        self.assertEqual(corrected["revision"], 2)
        self.assertEqual(corrected["difference"], {"start": 2, "delete_count": 3, "insert": "llo"})
        final = self.update(original)
        self.assertEqual(final["progress"], 100)
        self.assertTrue(final["complete"])
        self.race.refresh_from_db()
        self.assertEqual(self.race.race_text, original)
        self.assertEqual(self.race.status, Race.Status.FINISHED)
        self.entry.refresh_from_db()
        self.assertIsNotNone(self.entry.finished_at)
        self.assertIsNotNone(self.entry.wpm)

    def test_backspace_and_clear_are_saved(self):
        start_race(race_id=self.race.pk, player=self.player)
        self.update("hello")
        self.assertEqual(self.update("hel")["correct_prefix"], 3)
        self.assertEqual(self.update("")["progress"], 0)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.typed_text, "")
        self.assertEqual(self.entry.revision, 3)

    def test_invalid_text_and_nonparticipant_cannot_change_progress(self):
        start_race(race_id=self.race.pk, player=self.player)
        for text in [None, 42, ["h"], "x" * (len(self.paragraph.text) + 1)]:
            with self.assertRaises(ValidationError):
                self.update(text)
        other = get_user_model().objects.create_user(username="notjoined")
        with self.assertRaises(PermissionDenied):
            update_typing(race_id=self.race.pk, player_id=other.pk, text="h")
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.revision, 0)

    def test_manual_running_status_without_server_start_is_rejected(self):
        self.race.status = Race.Status.RUNNING
        self.race.save()
        with self.assertRaises(RaceConflict):
            self.update("h")
