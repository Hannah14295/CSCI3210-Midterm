"""Initialize an empty deployment without needing Render's paid shell feature."""
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from races.models import Paragraph


class Command(BaseCommand):
    help = "Seed an empty paragraph library and optionally create the first admin."

    @transaction.atomic
    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
        if bool(username) != bool(password):
            raise CommandError("Set both DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_PASSWORD, or neither.")

        if username:
            User = get_user_model()
            existing = User.objects.filter(username=username).first()
            if existing:
                if not (existing.is_staff and existing.is_superuser and existing.is_active):
                    raise CommandError("The requested admin username already belongs to a different or inactive account. Choose another username.")
                self.stdout.write("Admin already exists; credentials unchanged.")
            else:
                candidate = User(username=username)
                try:
                    candidate.full_clean(exclude=["password"])
                    validate_password(password, user=candidate)
                except ValidationError as error:
                    raise CommandError("Invalid initial admin settings: " + "; ".join(error.messages)) from error
                User.objects.create_superuser(
                    username=username,
                    password=password,
                    email=os.environ.get("DJANGO_SUPERUSER_EMAIL", ""),
                )
                self.stdout.write("Initial admin created.")

        if not Paragraph.objects.exists():
            Paragraph.objects.create(
                title="First practice race",
                text=(
                    "The small blue car waited at the starting line. "
                    "When the lights turned green, every driver focused on the road ahead. "
                    "Steady practice builds speed and accuracy."
                ),
            )
            self.stdout.write("Starter paragraph created.")
        else:
            self.stdout.write("Paragraph library already exists; passages unchanged.")
