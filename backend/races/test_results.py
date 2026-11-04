from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import Paragraph, Race, RaceParticipant
from .services import RaceConflict, start_race, update_typing
from .typing import calculate_wpm


class WPMTests(SimpleTestCase):
    def test_five_character_word_convention_and_rounding(self):
        self.assertEqual(calculate_wpm(300, 60), Decimal("60.00"))
        self.assertEqual(calculate_wpm(300, 30), Decimal("120.00"))
        self.assertEqual(calculate_wpm(1, 7), Decimal("1.71"))
        self.assertEqual(calculate_wpm(0, 10), Decimal("0.00"))
        self.assertEqual(calculate_wpm(10, 0), Decimal("0.00"))


class SavedResultTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.player = User.objects.create_user(username="resultplayer")
        self.other = User.objects.create_user(username="resultother")
        self.paragraph = Paragraph.objects.create(title="Result practice", text="hello world, practice today")
        self.race = Race.objects.create(host=self.player, paragraph=self.paragraph)
        self.entry = RaceParticipant.objects.create(race=self.race, player=self.player)
        self.other_entry = RaceParticipant.objects.create(race=self.race, player=self.other)
        start_race(race_id=self.race.pk, player=self.player)
        self.finish_time = timezone.now()
        self.start_time = self.finish_time - timedelta(seconds=60)
        Race.objects.filter(pk=self.race.pk).update(started_at=self.start_time)

    def submit(self, text, player=None):
        with patch("races.services.timezone.now", return_value=self.finish_time):
            return update_typing(race_id=self.race.pk, player_id=(player or self.player).pk, text=text)

    def test_full_length_input_saves_result_with_errors_using_server_elapsed_time(self):
        wrong = "x" + self.paragraph.text[1:]
        progress = self.submit(wrong[:5])
        self.assertFalse(progress["complete"])
        self.entry.refresh_from_db()
        self.assertIsNone(self.entry.finished_at)
        self.assertIsNone(self.entry.wpm)
        result = self.submit(wrong)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.finished_at, self.finish_time)
        self.assertEqual(self.entry.elapsed_seconds, Decimal("60.000000"))
        self.assertEqual(self.entry.wpm, calculate_wpm(len(self.paragraph.text) - 1, 60))
        self.assertEqual(result["wpm"], float(self.entry.wpm))
        self.assertLess(result["accuracy"], 100)
        self.race.refresh_from_db()
        self.assertEqual(self.race.status, Race.Status.FINISHED)

    def test_result_cannot_be_resubmitted_or_changed(self):
        self.submit(self.paragraph.text)
        self.entry.refresh_from_db()
        saved = (self.entry.finished_at, self.entry.wpm, self.entry.revision)
        for text in [self.paragraph.text, "", "hello"]:
            with self.assertRaises(RaceConflict):
                self.submit(text)
        self.entry.refresh_from_db()
        self.assertEqual((self.entry.finished_at, self.entry.wpm, self.entry.revision), saved)

    def test_first_finisher_ends_race_for_other_players(self):
        self.submit(self.paragraph.text)
        self.race.refresh_from_db()
        self.assertEqual(self.race.status, Race.Status.FINISHED)

        for text in ["hello", self.paragraph.text]:
            with self.assertRaises(RaceConflict):
                self.submit(text, player=self.other)

        self.other_entry.refresh_from_db()
        self.assertIsNone(self.other_entry.finished_at)
        self.assertIsNone(self.other_entry.wpm)
        self.assertEqual(self.other_entry.revision, 0)
        self.assertEqual(self.race.participants.filter(finished_at__isnull=False).count(), 1)

    def test_future_start_time_cannot_produce_a_score(self):
        Race.objects.filter(pk=self.race.pk).update(started_at=self.finish_time + timedelta(seconds=5))
        with self.assertRaises(RaceConflict):
            self.submit(self.paragraph.text)
        self.entry.refresh_from_db()
        self.assertIsNone(self.entry.wpm)


class LeaderboardTests(APITestCase):
    def setUp(self):
        self.player = get_user_model().objects.create_user(username="leader")
        paragraph = Paragraph.objects.create(title="Leaderboard", text="A paragraph for ranked results.")
        self.race = Race.objects.create(host=self.player, paragraph=paragraph)
        self.when = timezone.now()

    def result(self, wpm, when=None):
        # Different races allow multiple historical results for the same player.
        race = Race.objects.create(host=self.player, paragraph=self.race.paragraph)
        return RaceParticipant.objects.create(
            race=race, player=self.player, finished_at=when or self.when,
            elapsed_seconds=60, wpm=wpm,
        )

    def test_historical_results_are_ranked_and_unfinished_entries_excluded(self):
        slow = self.result(30)
        fast = self.result(90)
        tied_later = self.result(90, self.when + timedelta(seconds=1))
        RaceParticipant.objects.create(race=self.race, player=self.player)
        response = self.client.get(reverse("leaderboard-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 3)
        rows = response.data["results"]
        self.assertEqual([row["id"] for row in rows], [fast.pk, tied_later.pk, slow.pk])
        self.assertEqual([row["rank"] for row in rows], [1, 2, 3])
        self.assertEqual(set(rows[0]["player"]), {"id", "username"})

    def test_pagination_keeps_global_ranks_and_ties_are_stable(self):
        results = [self.result(50) for _ in range(21)]
        response = self.client.get(reverse("leaderboard-list"), {"page": 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["rank"], 21)
        self.assertEqual(response.data["results"][0]["id"], results[-1].pk)

    def test_leaderboard_cannot_accept_client_scores(self):
        self.client.force_authenticate(self.player)
        response = self.client.post(reverse("leaderboard-list"), {"wpm": 99999})
        self.assertEqual(response.status_code, 405)
        self.assertFalse(RaceParticipant.objects.exists())
