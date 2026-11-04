from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

User = get_user_model()


class AuthenticationTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.credentials = {
            "username": "testplayer",
            "password": "River!Track-49-Lantern",
        }

    def test_register_hashes_password_and_cannot_grant_admin_access(self):
        response = self.client.post(
            reverse("register"),
            {**self.credentials, "is_staff": True, "is_superuser": True},
        )
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(username="testplayer")
        self.assertTrue(user.check_password(self.credentials["password"]))
        self.assertNotEqual(user.password, self.credentials["password"])
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(set(response.data["user"]), {"id", "username"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {response.data['token']}")
        me = self.client.get(reverse("current-user"))
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["id"], user.pk)

    def test_invalid_registration_does_not_create_accounts(self):
        for payload in [
            {},
            {"username": "bad name!", "password": self.credentials["password"]},
            {"username": "player", "password": "123"},
            {"username": "player", "password": ""},
        ]:
            with self.subTest(payload_fields=list(payload)):
                self.assertEqual(self.client.post(reverse("register"), payload).status_code, 400)
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Token.objects.count(), 0)

    def test_duplicate_username_returns_validation_error(self):
        User.objects.create_user(**self.credentials)
        response = self.client.post(reverse("register"), self.credentials)
        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.data)
        self.assertEqual(User.objects.count(), 1)

    def test_login_checks_password_and_reuses_token(self):
        user = User.objects.create_user(**self.credentials)
        response = self.client.post(reverse("login"), self.credentials)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["id"], user.pk)
        again = self.client.post(reverse("login"), self.credentials)
        self.assertEqual(again.data["token"], response.data["token"])
        bad = self.client.post(reverse("login"), {**self.credentials, "password": "wrong"})
        self.assertEqual(bad.status_code, 400)

    def test_inactive_user_cannot_log_in_or_use_existing_token(self):
        user = User.objects.create_user(**self.credentials, is_active=False)
        token = Token.objects.create(user=user)
        self.assertEqual(self.client.post(reverse("login"), self.credentials).status_code, 400)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.assertEqual(self.client.get(reverse("current-user")).status_code, 401)

    def test_me_requires_valid_identity(self):
        self.assertEqual(self.client.get(reverse("current-user")).status_code, 401)
        self.client.credentials(HTTP_AUTHORIZATION="Token invalid-token")
        self.assertEqual(self.client.get(reverse("current-user")).status_code, 401)

    def test_me_returns_token_owner(self):
        first = User.objects.create_user(**self.credentials)
        User.objects.create_user(username="someoneelse")
        token = Token.objects.create(user=first)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.get(reverse("current-user"), {"username": "someoneelse"})
        self.assertEqual(response.data["username"], first.username)

    def test_login_is_throttled(self):
        for _ in range(30):
            self.assertEqual(self.client.post(reverse("login"), {}).status_code, 400)
        self.assertEqual(self.client.post(reverse("login"), {}).status_code, 429)
