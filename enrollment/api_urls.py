from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import api_views

router = DefaultRouter()
router.register("sessions", api_views.FormationSessionViewSet, basename="session")
router.register("offerings", api_views.OfferingViewSet, basename="offering")
router.register("clients", api_views.ClientViewSet, basename="client")
router.register("participants", api_views.ParticipantViewSet, basename="participant")
router.register("enrollments", api_views.EnrollmentViewSet, basename="enrollment")

urlpatterns = [
    # Public — write, creates Client + Participant(s) + Enrollment(s) in one call
    path("register/individual/", api_views.IndividualRegistrationView.as_view(), name="register-individual"),
    path("register/enterprise/", api_views.EnterpriseRegistrationView.as_view(), name="register-enterprise"),

    # Staff — JSON feed for the stats dashboard
    path("stats/dashboard/", api_views.DashboardStatsView.as_view(), name="stats-dashboard"),

    # Public catalog (read) + staff CRUD (clients/participants/enrollments)
    path("", include(router.urls)),
]
