from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import Client, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token

from config.asgi import application
from .models import Paragraph, Race, RaceParticipant
from .services import create_rematch, start_race


@override_settings(RACE_COUNTDOWN_SECONDS=0)
class RaceWebSocketTests(TransactionTestCase):
    def setUp(self):
        User = get_user_model()
        self.player = User.objects.create_user(username="socketplayer")
        self.other = User.objects.create_user(username="socketother")
        self.outsider = User.objects.create_user(username="outsider")
        self.token = Token.objects.create(user=self.player).key
        self.other_token = Token.objects.create(user=self.other).key
        self.outside_token = Token.objects.create(user=self.outsider).key
        paragraph = Paragraph.objects.create(title="Practice", text="A practice passage for live races.")
        self.race = Race.objects.create(host=self.player, paragraph=paragraph)
        self.other_race = Race.objects.create(host=self.outsider, paragraph=paragraph)
        RaceParticipant.objects.create(is_ready=True, race=self.race, player=self.player)
        RaceParticipant.objects.create(is_ready=True, race=self.race, player=self.other)
        RaceParticipant.objects.create(is_ready=True, race=self.other_race, player=self.outsider)
        client = Client()
        client.force_login(self.player)
        self.cookie = f"sessionid={client.cookies['sessionid'].value}".encode()

    def communicator(self, race_id=None, extra_headers=None):
        return WebsocketCommunicator(
            application, f"/ws/races/{race_id or self.race.pk}/",
            headers=[(b"origin", b"http://127.0.0.1:8000"), *(extra_headers or [])],
        )

    async def authenticate(self, socket, token):
        self.assertTrue((await socket.connect())[0])
        self.assertEqual((await socket.receive_json_from())["type"], "auth.required")
        await socket.send_json_to({"type": "authenticate", "token": token})
        return await socket.receive_json_from()

    async def test_broadcast_reaches_two_players_but_not_another_race(self):
        first = self.communicator()
        second = self.communicator()
        isolated = self.communicator(self.other_race.pk)
        try:
            self.assertEqual((await self.authenticate(first, self.token))["type"], "connected")
            await self.authenticate(second, self.other_token)
            await self.authenticate(isolated, self.outside_token)
            await first.send_json_to({
                "type": "demo.message", "text": "Hello race!",
                "player": {"id": self.outsider.pk}, "race_id": self.other_race.pk,
                "wpm": 9000,
            })
            message = await first.receive_json_from()
            self.assertEqual(message, await second.receive_json_from())
            self.assertEqual(message["player"]["id"], self.player.pk)
            self.assertEqual(message["race_id"], self.race.pk)
            self.assertEqual(message["text"], "Hello race!")
            self.assertNotIn("wpm", message)
            self.assertTrue(await isolated.receive_nothing())
        finally:
            await first.disconnect()
            await second.disconnect()
            await isolated.disconnect()

    async def test_admin_session_can_authenticate_without_token(self):
        socket = self.communicator(extra_headers=[(b"cookie", self.cookie)])
        try:
            self.assertTrue((await socket.connect())[0])
            response = await socket.receive_json_from()
            self.assertEqual(response["type"], "connected")
            self.assertEqual(response["player"]["id"], self.player.pk)
        finally:
            await socket.disconnect()

    async def test_waiting_room_keepalive_returns_current_snapshot_without_changing_scores(self):
        first = self.communicator()
        second = self.communicator()
        try:
            initial = await self.authenticate(first, self.token)
            await self.authenticate(second, self.other_token)
            for _ in range(2):
                await first.send_json_to({"type": "ping"})
                reply = await first.receive_json_from()
                self.assertEqual(reply["type"], "pong")
                self.assertEqual(reply["race"]["status"], initial["race"]["status"])
                self.assertEqual(reply["race"]["participants"], initial["race"]["participants"])
            self.assertTrue(await second.receive_nothing())
            await database_sync_to_async(start_race)(race_id=self.race.pk, player=self.player)
            await first.receive_json_from()
            await second.receive_json_from()
            await first.send_json_to({"type": "ping"})
            reply = await first.receive_json_from()
            self.assertEqual(reply["race"]["status"], "running")
            self.assertTrue(all(entry["revision"] == 0 for entry in reply["race"]["participants"]))
            self.assertTrue(all(entry["wpm"] is None for entry in reply["race"]["participants"]))
        finally:
            await first.disconnect()
            await second.disconnect()

    async def test_keepalive_does_not_bypass_token_revocation(self):
        socket = self.communicator()
        try:
            await self.authenticate(socket, self.token)
            await database_sync_to_async(lambda: Token.objects.filter(key=self.token).delete())()
            await socket.send_json_to({"type": "ping"})
            self.assertEqual((await socket.receive_output())["code"], 4403)
        finally:
            await socket.disconnect()

    async def test_explicit_token_mode_uses_player_token_instead_of_admin_cookie(self):
        socket = WebsocketCommunicator(
            application, f"/ws/races/{self.race.pk}/?auth=token",
            headers=[(b"origin", b"http://127.0.0.1:5173"), (b"cookie", self.cookie)],
        )
        try:
            connected = await self.authenticate(socket, self.other_token)
            self.assertEqual(connected["player"]["id"], self.other.pk)
            self.assertNotEqual(connected["player"]["id"], self.player.pk)
        finally:
            await socket.disconnect()

    async def test_nonparticipant_cannot_enter_room(self):
        socket = self.communicator()
        try:
            await socket.connect()
            await socket.receive_json_from()
            await socket.send_json_to({"type": "authenticate", "token": self.outside_token})
            self.assertEqual((await socket.receive_output())["code"], 4403)
        finally:
            await socket.disconnect()

    async def test_invalid_token_and_unauthenticated_message_are_rejected(self):
        for content in [
            {"type": "authenticate", "token": "x" * 40},
            {"type": "demo.message", "text": "Cannot send yet"},
        ]:
            socket = self.communicator()
            try:
                await socket.connect()
                await socket.receive_json_from()
                await socket.send_json_to(content)
                self.assertEqual((await socket.receive_output())["code"], 4401)
            finally:
                await socket.disconnect()

    async def test_invalid_packets_report_errors_without_breaking_connection(self):
        socket = self.communicator()
        try:
            await self.authenticate(socket, self.token)
            await socket.send_to(text_data="{broken json")
            self.assertEqual((await socket.receive_json_from())["type"], "error")
            for content in [[], {"type": "wrong"}, {"type": "demo.message", "text": "x" * 201}]:
                await socket.send_json_to(content)
                self.assertEqual((await socket.receive_json_from())["type"], "error")
            await socket.send_json_to({"type": "demo.message", "text": "Still works"})
            self.assertEqual((await socket.receive_json_from())["text"], "Still works")
        finally:
            await socket.disconnect()

    async def test_removing_participant_revokes_sending_access(self):
        socket = self.communicator()
        try:
            await self.authenticate(socket, self.token)
            await database_sync_to_async(
                lambda: RaceParticipant.objects.filter(race=self.race, player=self.player).delete()
            )()
            await socket.send_json_to({"type": "demo.message", "text": "No longer allowed"})
            self.assertEqual((await socket.receive_output())["code"], 4403)
        finally:
            await socket.disconnect()

    async def test_revoked_token_cannot_keep_sending(self):
        socket = self.communicator()
        try:
            await self.authenticate(socket, self.token)
            await database_sync_to_async(lambda: Token.objects.filter(key=self.token).delete())()
            await socket.send_json_to({"type": "demo.message", "text": "No longer allowed"})
            self.assertEqual((await socket.receive_output())["code"], 4403)
        finally:
            await socket.disconnect()

    async def test_untrusted_origin_is_rejected(self):
        socket = WebsocketCommunicator(application, f"/ws/races/{self.race.pk}/", headers=[
            (b"origin", b"https://untrusted.example"),
        ])
        try:
            self.assertFalse((await socket.connect())[0])
        finally:
            await socket.disconnect()

    async def test_github_pages_origin_can_connect_with_a_player_token(self):
        socket = WebsocketCommunicator(
            application, f"/ws/races/{self.race.pk}/?auth=token",
            headers=[(b"origin", b"https://hannah14295.github.io")],
        )
        try:
            connected = await self.authenticate(socket, self.token)
            self.assertEqual(connected["player"]["id"], self.player.pk)
        finally:
            await socket.disconnect()

    async def test_oversized_frame_is_closed(self):
        socket = self.communicator()
        try:
            await self.authenticate(socket, self.token)
            await socket.send_to(text_data="x" * 16385)
            self.assertEqual((await socket.receive_output())["code"], 1009)
        finally:
            await socket.disconnect()

    async def test_start_and_server_checked_progress_reach_both_tabs_and_reconnect(self):
        first = self.communicator()
        second = self.communicator()
        reconnected = None
        try:
            await self.authenticate(first, self.token)
            await self.authenticate(second, self.other_token)
            await database_sync_to_async(start_race)(race_id=self.race.pk, player=self.player)
            for socket in [first, second]:
                event = await socket.receive_json_from()
                self.assertEqual(event["type"], "race.updated")
                self.assertEqual(event["race"]["status"], "running")
                self.assertIsNotNone(event["race"]["started_at"])
            await first.send_json_to({"type": "typing.update", "text": "A practixe", "progress": 100, "player_id": self.other.pk})
            event = await first.receive_json_from()
            self.assertEqual(event, await second.receive_json_from())
            self.assertEqual(event["type"], "progress.updated")
            self.assertEqual(event["player"]["id"], self.player.pk)
            self.assertEqual(event["correct_prefix"], 8)
            self.assertLess(event["progress"], 100)
            self.assertFalse(event["complete"])
            reconnected = self.communicator()
            initial = await self.authenticate(reconnected, self.token)
            self.assertEqual(initial["your_text"], "A practixe")
            self.assertEqual(initial["race"]["paragraph_text"], "A practice passage for live races.")
            self.assertEqual(initial["race"]["participants"][0]["revision"], 1)
            await first.send_json_to({"type": "typing.update", "text": "A practice"})
            rejected = await first.receive_json_from()
            self.assertEqual(rejected["type"], "error")
            self.assertEqual(rejected["status"], 400)
            self.assertTrue(await second.receive_nothing())
            saved = await database_sync_to_async(
                lambda: RaceParticipant.objects.get(race=self.race, player=self.player).typed_text
            )()
            self.assertEqual(saved, "A practixe")
        finally:
            await first.disconnect()
            await second.disconnect()
            if reconnected:
                await reconnected.disconnect()

    async def test_typing_before_start_returns_error_and_saves_nothing(self):
        socket = self.communicator()
        try:
            await self.authenticate(socket, self.token)
            await socket.send_json_to({"type": "typing.update", "text": "A"})
            error = await socket.receive_json_from()
            self.assertEqual(error["type"], "error")
            self.assertEqual(error["status"], 409)
            revision = await database_sync_to_async(
                lambda: RaceParticipant.objects.get(race=self.race, player=self.player).revision
            )()
            self.assertEqual(revision, 0)
        finally:
            await socket.disconnect()

    async def test_rematch_broadcast_moves_both_players_and_is_recoverable_on_reconnect(self):
        await database_sync_to_async(lambda: Race.objects.filter(pk=self.race.pk).update(status=Race.Status.FINISHED))()
        first = self.communicator()
        second = self.communicator()
        reconnect = next_room = None
        try:
            await self.authenticate(first, self.token)
            await self.authenticate(second, self.other_token)
            race, created = await database_sync_to_async(create_rematch)(race_id=self.race.pk, player=self.player)
            self.assertTrue(created)
            event = await first.receive_json_from()
            self.assertEqual(event, await second.receive_json_from())
            self.assertEqual(event["type"], "race.updated")
            self.assertEqual(event["race"]["next_race_id"], race.pk)
            reconnect = self.communicator()
            restored = await self.authenticate(reconnect, self.other_token)
            self.assertEqual(restored["race"]["next_race_id"], race.pk)
            next_room = self.communicator(race.pk)
            initial = await self.authenticate(next_room, self.other_token)
            self.assertEqual(initial["race"]["status"], "waiting")
            self.assertEqual(initial["your_text"], "")
            self.assertEqual(len(initial["race"]["participants"]), 2)
        finally:
            await first.disconnect()
            await second.disconnect()
            if reconnect:
                await reconnect.disconnect()
            if next_room:
                await next_room.disconnect()

    async def test_finish_broadcasts_saved_result_and_reconnect_restores_it(self):
        await database_sync_to_async(start_race)(race_id=self.race.pk, player=self.player)
        socket = self.communicator()
        opponent = self.communicator()
        reconnect = None
        try:
            initial = await self.authenticate(socket, self.token)
            await self.authenticate(opponent, self.other_token)
            await socket.send_json_to({
                "type": "typing.update", "text": initial["race"]["paragraph_text"],
                "wpm": 999999, "elapsed_seconds": 1, "finished_at": "2020-01-01",
            })
            result = await socket.receive_json_from()
            self.assertEqual(result, await opponent.receive_json_from())
            self.assertEqual(result["type"], "progress.updated")
            self.assertTrue(result["complete"])
            self.assertIsNotNone(result["finished_at"])
            snapshot = await socket.receive_json_from()
            self.assertEqual(snapshot["type"], "race.updated")
            own_entry = snapshot["race"]["participants"][0]
            self.assertIsNotNone(own_entry["finished_at"])
            self.assertEqual(float(own_entry["wpm"]), result["wpm"])
            self.assertEqual(snapshot["race"]["status"], "running")
            self.assertEqual(snapshot, await opponent.receive_json_from())
            await socket.send_json_to({"type": "typing.update", "text": "changed"})
            self.assertEqual((await socket.receive_json_from())["status"], 409)
            await opponent.send_json_to({"type": "typing.update", "text": initial["race"]["paragraph_text"]})
            second_result = await opponent.receive_json_from()
            self.assertEqual(second_result["type"], "progress.updated")
            self.assertEqual(second_result, await socket.receive_json_from())
            final = await opponent.receive_json_from()
            self.assertEqual(final, await socket.receive_json_from())
            self.assertEqual(final["type"], "race.updated")
            self.assertEqual(final["race"]["status"], "finished")
            self.assertTrue(all(entry["finished_at"] for entry in final["race"]["participants"]))
            self.assertTrue(all(entry["wpm"] is not None and entry["accuracy"] is not None
                                for entry in final["race"]["participants"]))
            reconnect = self.communicator()
            restored = await self.authenticate(reconnect, self.token)
            self.assertEqual(restored["race"]["participants"][0]["wpm"], own_entry["wpm"])
            self.assertEqual(restored["race"]["status"], "finished")
            self.assertEqual(restored["race"]["participants"], final["race"]["participants"])
        finally:
            await socket.disconnect()
            await opponent.disconnect()
            if reconnect:
                await reconnect.disconnect()
