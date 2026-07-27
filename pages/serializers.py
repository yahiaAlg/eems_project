from rest_framework import serializers

from .models import Branch, Specialty, TrainingSession


class SpecialtySerializer(serializers.ModelSerializer):
    """A single specialty from the official nomenclature (مدونة الشعب المهنية)."""

    branch_code = serializers.CharField(source="branch.code", read_only=True)
    branch_name = serializers.CharField(source="branch.name_ar", read_only=True)

    class Meta:
        model = Specialty
        fields = ["id", "code", "name", "branch", "branch_code", "branch_name"]


class BranchListSerializer(serializers.ModelSerializer):
    """Lightweight variant used for list views — no nested specialties."""

    specialty_count = serializers.SerializerMethodField()

    class Meta:
        model = Branch
        fields = ["id", "code", "name_ar", "name_fr", "color", "order", "is_active", "specialty_count"]

    def get_specialty_count(self, obj):
        return obj.specialties.count()


class BranchDetailSerializer(BranchListSerializer):
    """Full variant used for retrieve views — includes every specialty in the branch."""

    specialties = SpecialtySerializer(many=True, read_only=True)

    class Meta(BranchListSerializer.Meta):
        fields = BranchListSerializer.Meta.fields + ["specialties"]


class TrainingSessionSerializer(serializers.ModelSerializer):
    """An upcoming/teaser training session as shown on the homepage
    (distinct from enrollment.FormationSession, which drives priced offerings
    and the registration flow)."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = TrainingSession
        fields = [
            "id", "title", "start_date", "duration_text",
            "seats", "status", "status_display", "is_active", "order",
        ]
