from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from rest_framework import generics, permissions, views, viewsets
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .models import Client, Enrollment, FormationSession, Offering, Participant
from .serializers import (
    ClientSerializer,
    EnterpriseRegistrationSerializer,
    EnrollmentSerializer,
    FormationSessionSerializer,
    IndividualRegistrationSerializer,
    OfferingSerializer,
    ParticipantSerializer,
)


class RegistrationThrottle(AnonRateThrottle):
    """Separate, tighter throttle scope for public write endpoints — configure the
    rate via REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["registration"] in settings.py."""

    scope = "registration"


# ---------------------------------------------------------------------------
# Public, read-only catalog
# ---------------------------------------------------------------------------


class FormationSessionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FormationSessionSerializer
    permission_classes = [permissions.AllowAny]
    queryset = FormationSession.objects.filter(is_active=True)


class OfferingViewSet(viewsets.ReadOnlyModelViewSet):
    """?session=<slug>&branch=<id>&level=<1-5> query params for filtering."""

    serializer_class = OfferingSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "code"

    def get_queryset(self):
        qs = (
            Offering.objects.filter(is_active=True, session__is_active=True)
            .select_related("session", "specialty__branch")
        )
        params = self.request.query_params
        session_slug = params.get("session")
        branch_id = params.get("branch")
        level = params.get("level")
        if session_slug:
            qs = qs.filter(session__slug=session_slug)
        if branch_id:
            qs = qs.filter(specialty__branch_id=branch_id)
        if level:
            qs = qs.filter(qualification_level=level)
        return qs


# ---------------------------------------------------------------------------
# Public registration (write-only) — POST creates Client + Participant(s) + Enrollment(s)
# ---------------------------------------------------------------------------


class IndividualRegistrationView(generics.CreateAPIView):
    """POST /api/register/individual/ — a private person registers themselves
    to one or more offerings."""

    serializer_class = IndividualRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [RegistrationThrottle]


class EnterpriseRegistrationView(generics.CreateAPIView):
    """POST /api/register/enterprise/ — a company registers a batch of its own
    employees (participants) to one or more offerings in a single call."""

    serializer_class = EnterpriseRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [RegistrationThrottle]


# ---------------------------------------------------------------------------
# Staff administration (CRUD, requires an authenticated staff/admin user)
# ---------------------------------------------------------------------------


class ClientViewSet(viewsets.ModelViewSet):
    """?client_type=individual|enterprise&source=web&search=<name/phone/email>"""

    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        qs = Client.objects.all().prefetch_related("participants", "enrollments__offering")
        params = self.request.query_params
        client_type = params.get("client_type")
        source = params.get("source")
        search = params.get("search")
        if client_type:
            qs = qs.filter(client_type=client_type)
        if source:
            qs = qs.filter(source=source)
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(full_name__icontains=search)
                | Q(company_name__icontains=search)
                | Q(phone__icontains=search)
                | Q(email__icontains=search)
            )
        return qs.distinct()


class ParticipantViewSet(viewsets.ModelViewSet):
    serializer_class = ParticipantSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        qs = Participant.objects.select_related("client")
        client_id = self.request.query_params.get("client")
        if client_id:
            qs = qs.filter(client_id=client_id)
        return qs


class EnrollmentViewSet(viewsets.ModelViewSet):
    """?status=pending&offering=<id>&session=<slug>&client_type=individual|enterprise"""

    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        qs = Enrollment.objects.select_related("client", "participant", "offering__session")
        params = self.request.query_params
        status_ = params.get("status")
        offering_id = params.get("offering")
        session_slug = params.get("session")
        client_type = params.get("client_type")
        if status_:
            qs = qs.filter(status=status_)
        if offering_id:
            qs = qs.filter(offering_id=offering_id)
        if session_slug:
            qs = qs.filter(offering__session__slug=session_slug)
        if client_type:
            qs = qs.filter(client__client_type=client_type)
        return qs

    def perform_update(self, serializer):
        serializer.save(handled_by=self.request.user)


class DashboardStatsView(views.APIView):
    """GET /api/stats/dashboard/ — JSON feed for the admin stats dashboard."""

    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        clients = Client.objects.all()
        enrollments = Enrollment.objects.all()

        data = {
            "clients_total": clients.count(),
            "clients_individual": clients.filter(client_type="individual").count(),
            "clients_enterprise": clients.filter(client_type="enterprise").count(),
            "enrollments_today": enrollments.filter(created_at__date=today).count(),
            "enrollments_month": enrollments.filter(
                created_at__year=today.year, created_at__month=today.month,
            ).count(),
            "enrollments_total": enrollments.count(),
            "by_status": list(enrollments.values("status").annotate(count=Count("id"))),
            "by_source": list(clients.values("source").annotate(count=Count("id"))),
            "by_client_type": list(clients.values("client_type").annotate(count=Count("id"))),
            "by_offering": list(
                enrollments.values("offering__code", "offering__title")
                .annotate(count=Count("id"))
                .order_by("-count")[:10]
            ),
            "daily_last_week": list(
                enrollments.filter(created_at__date__gte=week_ago)
                .values("created_at__date")
                .annotate(count=Count("id"))
                .order_by("created_at__date")
            ),
        }
        return Response(data)
