from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import Client, TransactionTestCase
from rest_framework.authtoken.models import Token

from config.asgi import application
from .models import Paragraph, Race, RaceParticipant


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
        RaceParticipant.objects.create(race=self.race, player=self.player)
        RaceParticipant.objects.create(race=self.race, player=self.other)
        RaceParticipant.objects.create(race=self.other_race, player=self.outsider)
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

    async def test_oversized_frame_is_closed(self):
        socket = self.communicator()
        try:
            await self.authenticate(socket, self.token)
            await socket.send_to(text_data="x" * 4097)
            self.assertEqual((await socket.receive_output())["code"], 1009)
        finally:
            await socket.disconnect()
