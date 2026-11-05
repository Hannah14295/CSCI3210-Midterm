from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from .models import Paragraph, Race, RaceParticipant
from .services import RaceConflict, start_race, update_typing
from .typing import calculate_wpm


@override_settings(RACE_COUNTDOWN_SECONDS=3)
class CountdownClockTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.host = User.objects.create_user(username="countdownhost")
        self.guest = User.objects.create_user(username="countdownguest")
        paragraph = Paragraph.objects.create(title="Countdown", text="hello world, a fresh typing race")
        self.race = Race.objects.create(host=self.host, paragraph=paragraph)
        self.first = RaceParticipant.objects.create(is_ready=True, race=self.race, player=self.host)
        self.second = RaceParticipant.objects.create(is_ready=True, race=self.race, player=self.guest)
        self.clicked = timezone.now()
        with patch("races.services.timezone.now", return_value=self.clicked):
            start_race(race_id=self.race.pk, player=self.host)
        self.race.refresh_from_db()
        self.go = self.clicked + timedelta(seconds=3)

    def type(self, player, text, seconds_after_go):
        with patch("races.services.timezone.now", return_value=self.go + timedelta(seconds=seconds_after_go)):
            return update_typing(race_id=self.race.pk, player_id=player.pk, text=text)

    def test_countdown_uses_a_shared_future_go_time_and_blocks_early_input(self):
        self.assertEqual(self.race.started_at, self.go)
        for player in (self.host, self.guest):
            with self.assertRaises(RaceConflict):
                self.type(player, "h", -0.01)
        self.first.refresh_from_db()
        self.assertIsNone(self.first.typing_started_at)
        self.assertEqual(self.first.typed_text, "")
        self.assertEqual(self.first.revision, 0)

    def test_empty_updates_do_not_start_the_clock_and_waiting_time_is_excluded(self):
        self.type(self.host, "", 20)
        self.first.refresh_from_db()
        self.assertIsNone(self.first.typing_started_at)
        first_key = self.type(self.host, "h", 30)
        self.assertEqual(first_key["wpm"], 0)
        self.type(self.host, self.race.race_text, 40)
        self.first.refresh_from_db()
        self.assertEqual(self.first.typing_started_at, self.go + timedelta(seconds=30))
        self.assertEqual(self.first.elapsed_seconds, Decimal("10.000000"))
        self.assertEqual(self.first.wpm, calculate_wpm(len(self.race.race_text), 10))

    def test_players_have_independent_start_times_and_neither_is_reset(self):
        self.type(self.host, "h", 2)
        self.type(self.host, "he", 5)
        self.type(self.host, self.race.race_text, 12)
        self.type(self.guest, "h", 20)
        self.type(self.guest, self.race.race_text, 40)
        self.first.refresh_from_db()
        self.second.refresh_from_db()
        self.race.refresh_from_db()
        self.assertEqual(self.first.typing_started_at, self.go + timedelta(seconds=2))
        self.assertEqual(self.second.typing_started_at, self.go + timedelta(seconds=20))
        self.assertEqual(self.first.elapsed_seconds, Decimal(10))
        self.assertEqual(self.second.elapsed_seconds, Decimal(20))
        self.assertEqual(self.race.status, Race.Status.FINISHED)

    def test_first_packet_completion_still_has_a_valid_positive_duration(self):
        self.type(self.host, self.race.race_text, 10)
        self.first.refresh_from_db()
        self.assertGreater(self.first.elapsed_seconds, 0)
        self.assertIsNotNone(self.first.finished_at)
