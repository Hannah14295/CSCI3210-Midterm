from rest_framework.routers import DefaultRouter

from .views import ParagraphViewSet

router = DefaultRouter()
router.register("paragraphs", ParagraphViewSet, basename="paragraph")
urlpatterns = router.urls
