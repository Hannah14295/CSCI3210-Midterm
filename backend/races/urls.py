from rest_framework.routers import DefaultRouter

from .views import ParagraphViewSet, RaceViewSet

router = DefaultRouter()
router.register("paragraphs", ParagraphViewSet, basename="paragraph")
router.register("races", RaceViewSet, basename="race")
urlpatterns = router.urls
