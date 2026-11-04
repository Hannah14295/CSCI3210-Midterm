"""Authenticated race-room transport and server-validated typing updates."""
import asyncio
import json
from collections import deque
from time import monotonic
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import APIException

from .models import RaceParticipant
from .events import race_snapshot
from .services import update_typing


class RaceConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.race_id = self.scope["url_route"]["kwargs"]["race_id"]
        self.room = f"race.{self.race_id}"
        self.player_id = None
        self.auth_token = None
        self.joined_group = False
        self.auth_timer = None
        self.message_times = deque()
        await self.accept()
        user = self.scope.get("user")
        token_mode = parse_qs(self.scope.get("query_string", b"").decode()).get("auth") == ["token"]
        if user and user.is_authenticated and not token_mode:
            self.player_id = user.pk
            await self.enter_room()
        else:
            await self.send_json({"type": "auth.required"})
            self.auth_timer = asyncio.create_task(self.authentication_timeout())

    async def authentication_timeout(self):
        await asyncio.sleep(10)
        await self.close(code=4401)

    async def disconnect(self, code):
        if self.auth_timer:
            self.auth_timer.cancel()
        if self.joined_group:
            await self.channel_layer.group_discard(self.room, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        if text_data is None:
            await self.close(code=1003)
            return
        if len(text_data) > 16384:
            await self.close(code=1009)
            return
        now = monotonic()
        while self.message_times and self.message_times[0] < now - 1:
            self.message_times.popleft()
        if len(self.message_times) >= 10:
            await self.close(code=4429)
            return
        self.message_times.append(now)
        try:
            content = json.loads(text_data)
        except (ValueError, RecursionError):
            await self.send_json({"type": "error", "detail": "Send a JSON object."})
            return
        if not isinstance(content, dict):
            await self.send_json({"type": "error", "detail": "Send a JSON object."})
            return
        await self.receive_json(content)

    async def receive_json(self, content, **kwargs):
        if self.player_id is None:
            token = content.get("token")
            if content.get("type") != "authenticate" or not isinstance(token, str) or len(token) != 40:
                await self.close(code=4401)
                return
            self.player_id = await self.token_owner(token)
            if self.player_id is None:
                await self.close(code=4401)
                return
            self.auth_token = token
            if self.auth_timer:
                self.auth_timer.cancel()
            await self.enter_room()
            return

        access = await self.access()
        if access is None:
            await self.close(code=4403)
            return
        text = content.get("text")
        if content.get("type") == "typing.update":
            try:
                await database_sync_to_async(update_typing)(
                    race_id=self.race_id, player_id=self.player_id, text=text,
                )
            except APIException as error:
                await self.send_json({"type": "error", "status": error.status_code, "detail": error.detail})
            return
        if content.get("type") != "demo.message" or not isinstance(text, str) or not text.strip() or len(text) > 200:
            await self.send_json({"type": "error", "detail": "Send typing.update, or demo.message with 1-200 characters of text."})
            return
        # Never trust client-supplied player IDs, room IDs, or score fields.
        await self.channel_layer.group_send(self.room, {
            "type": "race.message",
            "payload": {
                "type": "demo.message",
                "race_id": self.race_id,
                "player": {"id": self.player_id, "username": access["player__username"]},
                "text": text,
            },
        })

    async def enter_room(self):
        access = await self.access()
        if access is None:
            await self.close(code=4403)
            return
        await self.channel_layer.group_add(self.room, self.channel_name)
        self.joined_group = True
        await self.send_json({
            "type": "connected",
            "race_id": self.race_id,
            "player": {"id": self.player_id, "username": access["player__username"]},
            "race": await database_sync_to_async(race_snapshot)(self.race_id),
            "your_text": await self.saved_text(),
        })

    async def race_message(self, event):
        if await self.access() is None:
            await self.close(code=4403)
            return
        await self.send_json(event["payload"])

    @database_sync_to_async
    def token_owner(self, key):
        return Token.objects.filter(key=key, user__is_active=True).values_list("user_id", flat=True).first()

    @database_sync_to_async
    def saved_text(self):
        return RaceParticipant.objects.get(race_id=self.race_id, player_id=self.player_id).typed_text

    @database_sync_to_async
    def access(self):
        if self.auth_token and not Token.objects.filter(key=self.auth_token, user_id=self.player_id).exists():
            return None
        return RaceParticipant.objects.filter(
            race_id=self.race_id, player_id=self.player_id, player__is_active=True,
        ).values("player__username").first()
