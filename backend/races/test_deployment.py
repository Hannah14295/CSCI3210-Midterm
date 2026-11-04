"""Checks for the configuration used by GitHub Pages and Render."""
import os
import runpy
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase
from rest_framework.test import APITestCase


class DeploymentConfigurationTests(SimpleTestCase):
    def read_settings(self, **environment):
        with patch.dict(os.environ, environment):
            return runpy.run_path(str(settings.BASE_DIR / "config" / "settings.py"))

    def test_render_uses_postgres_redis_and_https_without_connecting(self):
        config = self.read_settings(
            RENDER="true",
            RENDER_EXTERNAL_HOSTNAME="typing-test.onrender.com",
            DJANGO_DEBUG="False",
            DATABASE_URL="postgresql://testuser:testpassword@localhost:5432/testdb",
            REDIS_URL="redis://localhost:6379/0",
            FRONTEND_ORIGINS="https://hannah14295.github.io",
        )
        self.assertIn("typing-test.onrender.com", config["ALLOWED_HOSTS"])
        self.assertEqual(config["DATABASES"]["default"]["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(config["DATABASES"]["default"]["CONN_MAX_AGE"], 0)
        self.assertEqual(config["CHANNEL_LAYERS"]["default"]["BACKEND"], "channels_redis.core.RedisChannelLayer")
        self.assertEqual(config["CACHES"]["default"]["BACKEND"], "django.core.cache.backends.redis.RedisCache")
        self.assertTrue(config["SECURE_SSL_REDIRECT"])
        self.assertTrue(config["SESSION_COOKIE_SECURE"])
        self.assertEqual(config["CORS_ALLOWED_ORIGINS"], ["https://hannah14295.github.io"])
        self.assertIn("https://hannah14295.github.io", config["WEBSOCKET_ALLOWED_ORIGINS"])
        self.assertFalse(config["CORS_ALLOW_CREDENTIALS"])

    def test_local_fallback_still_uses_sqlite_and_in_memory_messages(self):
        config = self.read_settings(RENDER="", DATABASE_URL="", REDIS_URL="", DJANGO_DEBUG="True")
        self.assertEqual(config["DATABASES"]["default"]["ENGINE"], "django.db.backends.sqlite3")
        self.assertEqual(config["CHANNEL_LAYERS"]["default"]["BACKEND"], "channels.layers.InMemoryChannelLayer")
        self.assertFalse(config["SESSION_COOKIE_SECURE"])

    def test_render_cannot_silently_use_temporary_sqlite_or_local_messages(self):
        for database, redis in [("", ""), ("postgresql://localhost/testdb", ""), ("", "redis://localhost:6379/0")]:
            with self.subTest(database_configured=bool(database), redis_configured=bool(redis)):
                with self.assertRaises(ImproperlyConfigured):
                    self.read_settings(RENDER="true", DATABASE_URL=database, REDIS_URL=redis)


class CrossOriginAPITests(APITestCase):
    def test_github_pages_can_preflight_a_token_request(self):
        response = self.client.options(
            "/api/races/",
            HTTP_ORIGIN="https://hannah14295.github.io",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Access-Control-Allow-Origin"], "https://hannah14295.github.io")
        self.assertIn("authorization", response["Access-Control-Allow-Headers"])

    def test_allowed_origin_can_read_authentication_errors(self):
        response = self.client.get("/api/races/", HTTP_ORIGIN="https://hannah14295.github.io")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response["Access-Control-Allow-Origin"], "https://hannah14295.github.io")

    def test_unknown_origin_does_not_get_cors_permission(self):
        response = self.client.get("/api/paragraphs/", HTTP_ORIGIN="https://untrusted.example")
        self.assertNotIn("Access-Control-Allow-Origin", response)
