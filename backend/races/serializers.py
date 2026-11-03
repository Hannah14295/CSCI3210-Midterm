from rest_framework import serializers

from .models import Paragraph


class ParagraphSerializer(serializers.ModelSerializer):
    """Choose which model fields the API exposes as JSON."""

    class Meta:
        model = Paragraph
        fields = ["id", "title", "text"]
        read_only_fields = fields
