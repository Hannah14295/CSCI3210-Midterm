from rest_framework.routers import DefaultRouter

from .views import ParagraphViewSet, RaceViewSet, LeaderboardViewSet

router = DefaultRouter()
router.register("paragraphs", ParagraphViewSet, basename="paragraph")
router.register("races", RaceViewSet, basename="race")
router.register("leaderboard", LeaderboardViewSet, basename="leaderboard")
urlpatterns = router.urls
