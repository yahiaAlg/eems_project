from rest_framework.routers import DefaultRouter

from . import api_views

router = DefaultRouter()
router.register("branches", api_views.BranchViewSet, basename="branch")
router.register("specialties", api_views.SpecialtyViewSet, basename="specialty")
router.register("trainings", api_views.TrainingSessionViewSet, basename="training")

urlpatterns = router.urls
