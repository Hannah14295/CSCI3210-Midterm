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
