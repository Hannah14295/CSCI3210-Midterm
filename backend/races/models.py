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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"Race {self.pk} ({self.get_status_display()})"
