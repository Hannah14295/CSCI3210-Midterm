from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet

from .models import Paragraph
from .serializers import ParagraphSerializer


class ParagraphViewSet(ReadOnlyModelViewSet):
    """Anyone can read practice text; only admin users can edit it via admin."""

    queryset = Paragraph.objects.all()
    serializer_class = ParagraphSerializer
    permission_classes = [AllowAny]
