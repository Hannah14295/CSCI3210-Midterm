from django.conf import settings
from django.core.validators import MinLengthValidator, RegexValidator
from django.db import models


class Paragraph(models.Model):
    """A saved passage that players will type during a race."""

    title = models.CharField(max_length=100)
    text = models.TextField(
        max_length=2000,
        validators=[
            MinLengthValidator(20),
            RegexValidator(r"\S", "The paragraph must contain non-whitespace text."),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.title


class Race(models.Model):
    """A race links a passage and a host to a saved race status."""

    class Status(models.TextChoices):
        WAITING = "waiting", "Waiting"
        RUNNING = "running", "Running"
        FINISHED = "finished", "Finished"

    paragraph = models.ForeignKey(
        Paragraph,
        on_delete=models.PROTECT,
        related_name="races",
    )
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="hosted_races",
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.WAITING,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    race_text = models.TextField(max_length=2000, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"Race {self.pk} ({self.get_status_display()})"


class RaceParticipant(models.Model):
    """One player's entry in one race."""

    race = models.ForeignKey(
        Race,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    player = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="race_entries",
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    typed_text = models.TextField(max_length=2000, blank=True, default="")
    revision = models.PositiveIntegerField(default=0)
    finished_at = models.DateTimeField(null=True, blank=True)
    elapsed_seconds = models.DecimalField(max_digits=14, decimal_places=6, null=True, blank=True)
    wpm = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ["joined_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["race", "player"],
                name="unique_player_per_race",
            )
        ]

    def __str__(self):
        return f"{self.player} in race {self.race_id}"
