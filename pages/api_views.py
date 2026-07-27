from django.db.models import Q
from rest_framework import permissions, viewsets

from .models import Branch, Specialty, TrainingSession
from .serializers import (
    BranchDetailSerializer,
    BranchListSerializer,
    SpecialtySerializer,
    TrainingSessionSerializer,
)


class BranchViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/pages/branches/ — the 23 professional branches.
    GET /api/pages/branches/<code>/ — one branch with all its specialties nested."""

    permission_classes = [permissions.AllowAny]
    lookup_field = "code"
    queryset = Branch.objects.filter(is_active=True).order_by("order")

    def get_serializer_class(self):
        return BranchDetailSerializer if self.action == "retrieve" else BranchListSerializer


class SpecialtyViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/pages/specialties/ — the ~495 specialties from the nomenclature.
    Filters: ?branch=<branch_code>&search=<code_or_name>"""

    permission_classes = [permissions.AllowAny]
    serializer_class = SpecialtySerializer
    lookup_field = "code"

    def get_queryset(self):
        qs = Specialty.objects.select_related("branch").order_by("branch__order", "code")
        params = self.request.query_params
        branch_code = params.get("branch")
        search = params.get("search")
        if branch_code:
            qs = qs.filter(branch__code=branch_code)
        if search:
            qs = qs.filter(Q(code__icontains=search) | Q(name__icontains=search))
        return qs


class TrainingSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/pages/trainings/ — upcoming-sessions teaser shown on the homepage."""

    permission_classes = [permissions.AllowAny]
    serializer_class = TrainingSessionSerializer
    queryset = TrainingSession.objects.filter(is_active=True).order_by("start_date")
