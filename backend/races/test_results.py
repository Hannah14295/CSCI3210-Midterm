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
        self.assertIsNone(self.entry.accuracy)
        result = self.submit(wrong)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.finished_at, self.finish_time)
        self.assertEqual(self.entry.elapsed_seconds, Decimal("60.000000"))
        self.assertEqual(self.entry.wpm, calculate_wpm(len(self.paragraph.text) - 1, 60))
        self.assertEqual(result["wpm"], float(self.entry.wpm))
        self.assertLess(result["accuracy"], 100)
        self.assertEqual(self.entry.accuracy, Decimal(str(result["accuracy"])))
        self.race.refresh_from_db()
        self.assertEqual(self.race.status, Race.Status.RUNNING)

    def test_result_cannot_be_resubmitted_or_changed(self):
        self.submit(self.paragraph.text)
        self.entry.refresh_from_db()
        saved = (self.entry.finished_at, self.entry.wpm, self.entry.accuracy, self.entry.revision)
        for text in [self.paragraph.text, "", "hello"]:
            with self.assertRaises(RaceConflict):
                self.submit(text)
        self.entry.refresh_from_db()
        self.assertEqual((self.entry.finished_at, self.entry.wpm, self.entry.accuracy, self.entry.revision), saved)

    def test_first_finisher_waits_and_other_players_can_finish(self):
        self.submit(self.paragraph.text)
        self.race.refresh_from_db()
        self.assertEqual(self.race.status, Race.Status.RUNNING)
        self.submit("hello", player=self.other)
        self.other_entry.refresh_from_db()
        self.assertIsNone(self.other_entry.finished_at)
        self.submit(self.paragraph.text, player=self.other)
        self.race.refresh_from_db()
        self.other_entry.refresh_from_db()
        self.assertEqual(self.race.status, Race.Status.FINISHED)
        self.assertIsNotNone(self.other_entry.wpm)
        self.assertEqual(self.other_entry.accuracy, Decimal("100.00"))
        self.assertEqual(self.race.participants.filter(finished_at__isnull=False).count(), 2)

    def test_three_players_wait_for_the_last_finish_and_keep_individual_times(self):
        third = get_user_model().objects.create_user(username="thirdfinisher")
        RaceParticipant.objects.create(race=self.race, player=third)
        self.submit(self.paragraph.text)
        self.finish_time += timedelta(seconds=10)
        self.submit("x" + self.paragraph.text[1:], player=self.other)
        self.race.refresh_from_db()
        self.assertEqual(self.race.status, Race.Status.RUNNING)
        self.finish_time += timedelta(seconds=10)
        self.submit(self.paragraph.text, player=third)
        self.race.refresh_from_db()
        self.assertEqual(self.race.status, Race.Status.FINISHED)
        durations = list(self.race.participants.order_by("finished_at").values_list("elapsed_seconds", flat=True))
        self.assertEqual(durations, [Decimal(60), Decimal(70), Decimal(80)])

    def test_solo_practice_finishes_when_the_only_player_finishes(self):
        self.other_entry.delete()
        self.submit(self.paragraph.text)
        self.race.refresh_from_db()
        self.assertEqual(self.race.status, Race.Status.FINISHED)

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

    def result(self, wpm, when=None, accuracy=None):
        # Different races allow multiple historical results for the same player.
        race = Race.objects.create(host=self.player, paragraph=self.race.paragraph)
        return RaceParticipant.objects.create(
            race=race, player=self.player, finished_at=when or self.when,
            elapsed_seconds=60, wpm=wpm, accuracy=accuracy,
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

    def test_accuracy_ranks_all_results_independently_with_wpm_breaking_ties(self):
        fastest = self.result(120, accuracy=80)
        precise = self.result(30, accuracy=100)
        precise_faster = self.result(60, accuracy=100)
        missing = self.result(200)  # No trustworthy historical accuracy.
        zero = self.result(0, accuracy=0)
        url = reverse("leaderboard-list")
        speed = self.client.get(url, {"metric": "wpm", "limit": 10})
        self.assertEqual([row["id"] for row in speed.data["results"]],
                         [missing.pk, fastest.pk, precise_faster.pk, precise.pk, zero.pk])
        accuracy = self.client.get(url, {"metric": "accuracy", "limit": 10})
        self.assertEqual(accuracy.status_code, 200)
        self.assertEqual([row["id"] for row in accuracy.data["results"]],
                         [precise_faster.pk, precise.pk, fastest.pk, zero.pk])
        self.assertEqual([row["rank"] for row in accuracy.data["results"]], [1, 2, 3, 4])
        self.assertEqual(float(accuracy.data["results"][0]["accuracy"]), 100)

    def test_each_board_returns_only_the_ten_best_results_when_requested(self):
        entries = [self.result(20 + i, accuracy=80 + i) for i in range(15)]
        for metric in ("wpm", "accuracy"):
            response = self.client.get(reverse("leaderboard-list"), {"metric": metric, "limit": 10})
            self.assertEqual(response.status_code, 200)
            rows = response.data["results"]
            self.assertEqual(len(rows), 10)
            self.assertEqual([row["id"] for row in rows], [entry.pk for entry in reversed(entries[-10:])])
            self.assertEqual([row["rank"] for row in rows], list(range(1, 11)))

    def test_unknown_ranking_metric_is_rejected(self):
        response = self.client.get(reverse("leaderboard-list"), {"metric": "client_score"})
        self.assertEqual(response.status_code, 400)

    def test_accuracy_backfill_uses_saved_text_and_skips_incomplete_history(self):
        from importlib import import_module
        from types import SimpleNamespace
        from django.apps import apps
        from django.db import connection

        known = self.result(30)
        known.race.race_text = "hello"
        known.race.save(update_fields=["race_text"])
        known.typed_text = "hexlo"
        known.save(update_fields=["typed_text"])
        unknown = self.result(90)
        self.race.paragraph.text = "The passage was edited after the race."
        self.race.paragraph.save()

        migration = import_module("races.migrations.0007_raceparticipant_accuracy")
        migration.backfill_accuracy(apps, SimpleNamespace(connection=connection))
        known.refresh_from_db()
        unknown.refresh_from_db()
        self.assertEqual(known.accuracy, Decimal("80.00"))
        self.assertIsNone(unknown.accuracy)
