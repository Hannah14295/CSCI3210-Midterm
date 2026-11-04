import os
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from races.models import Paragraph


class DeploymentBootstrapTests(TestCase):
    def run_bootstrap(self, username="", password=""):
        output = StringIO()
        with patch.dict(os.environ, {
            "DJANGO_SUPERUSER_USERNAME": username,
            "DJANGO_SUPERUSER_PASSWORD": password,
        }):
            call_command("bootstrap_deployment", stdout=output)
        return output.getvalue()

    def test_empty_library_is_seeded_once(self):
        self.run_bootstrap()
        paragraph = Paragraph.objects.get()
        paragraph.text = "My own passage must not be overwritten."
        paragraph.save()
        self.run_bootstrap()
        self.assertEqual(Paragraph.objects.count(), 1)
        paragraph.refresh_from_db()
        self.assertEqual(paragraph.text, "My own passage must not be overwritten.")
        self.assertFalse(get_user_model().objects.exists())

    def test_admin_is_created_with_hashed_password_and_never_reset(self):
        password = "Local-Test-Only!Sunrise-814"
        output = self.run_bootstrap("deployadmin", password)
        user = get_user_model().objects.get(username="deployadmin")
        self.assertTrue(user.is_superuser and user.is_staff)
        self.assertTrue(user.check_password(password))
        self.assertNotIn(password, output)
        self.run_bootstrap("deployadmin", "A-Different!Test-Password-97")
        user.refresh_from_db()
        self.assertTrue(user.check_password(password))

    def test_regular_account_cannot_be_promoted_by_startup(self):
        user = get_user_model().objects.create_user(username="existing")
        with self.assertRaises(CommandError):
            self.run_bootstrap("existing", "Local-Test-Only!Sunrise-814")
        user.refresh_from_db()
        self.assertFalse(user.is_superuser)

    def test_partial_or_weak_admin_credentials_are_rejected(self):
        for username, password in [("admin", ""), ("", "somepassword"), ("admin", "123")]:
            with self.assertRaises(CommandError):
                self.run_bootstrap(username, password)
        self.assertFalse(get_user_model().objects.exists())
        self.assertFalse(Paragraph.objects.exists())

    def test_health_route_is_public(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
