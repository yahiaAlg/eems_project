from django.db import transaction
from rest_framework import serializers

from .models import (
    Client,
    Enrollment,
    EnrollmentNote,
    FormationSession,
    GENDER_CHOICES,
    Offering,
    Participant,
    SOURCE_CHOICES,
)

# ---------------------------------------------------------------------------
# Catalog (read-only, public)
# ---------------------------------------------------------------------------


class FormationSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormationSession
        fields = ["id", "name", "slug", "start_date", "registration_deadline", "is_active"]


class OfferingSerializer(serializers.ModelSerializer):
    session = FormationSessionSerializer(read_only=True)
    seats_taken = serializers.ReadOnlyField()
    seats_remaining = serializers.ReadOnlyField()
    fill_rate = serializers.ReadOnlyField()
    tasks_list = serializers.ReadOnlyField()
    qualification_level_display = serializers.CharField(
        source="get_qualification_level_display", read_only=True,
    )
    certificate_type_display = serializers.CharField(
        source="get_certificate_type_display", read_only=True,
    )
    specialty_code = serializers.CharField(source="specialty.code", read_only=True, default=None)
    branch_code = serializers.CharField(source="specialty.branch.code", read_only=True, default=None)

    class Meta:
        model = Offering
        fields = [
            "id", "session", "code", "title", "branch_label",
            "specialty_code", "branch_code",
            "qualification_level", "qualification_level_display",
            "certificate_type", "certificate_type_display", "entry_level",
            "duration_months", "monthly_fee", "total_fee",
            "seats_available", "seats_taken", "seats_remaining", "fill_rate",
            "description", "tasks_list", "image",
        ]

    # Fields dropped from the public catalog API response for
    # anonymous/non-VIP callers (TODO 3.3 pricing-visibility rule, same
    # helper enrollment/views.py uses for the HTML pages — lazy-imported
    # here to avoid a module-load-order dependency on enrollment.views).
    PRICE_FIELDS = ("monthly_fee", "total_fee")

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        if request is not None:
            from .views import _can_view_prices

            if not _can_view_prices(request):
                for field in self.PRICE_FIELDS:
                    data.pop(field, None)
        return data


# ---------------------------------------------------------------------------
# Administration (staff-only CRUD)
# ---------------------------------------------------------------------------


class ParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Participant
        fields = [
            "id", "client", "full_name", "phone", "email",
            "birth_date", "gender", "education_level", "position",
        ]


class EnrollmentNoteSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = EnrollmentNote
        fields = ["id", "text", "author", "created_at"]
        read_only_fields = ["author", "created_at"]


class EnrollmentSerializer(serializers.ModelSerializer):
    """Staff view/administration of a single participant's registration in one offering."""

    participant = ParticipantSerializer(read_only=True)
    participant_id = serializers.PrimaryKeyRelatedField(
        queryset=Participant.objects.all(), source="participant", write_only=True,
    )
    offering = OfferingSerializer(read_only=True)
    offering_id = serializers.PrimaryKeyRelatedField(
        queryset=Offering.objects.all(), source="offering", write_only=True,
    )
    client_name = serializers.CharField(source="client.display_name", read_only=True)
    client_type = serializers.CharField(source="client.client_type", read_only=True)
    notes = EnrollmentNoteSerializer(many=True, read_only=True)

    class Meta:
        model = Enrollment
        fields = [
            "id", "client", "client_name", "client_type",
            "participant", "participant_id", "offering", "offering_id",
            "status", "motivation", "handled_by", "created_at", "updated_at", "notes",
        ]
        read_only_fields = ["client", "created_at", "updated_at"]


class ClientSerializer(serializers.ModelSerializer):
    """Full staff-facing detail of a client, including nested participants & enrollments."""

    participants = ParticipantSerializer(many=True, read_only=True)
    enrollments = EnrollmentSerializer(many=True, read_only=True)
    display_name = serializers.ReadOnlyField()

    class Meta:
        model = Client
        fields = [
            "id", "client_type", "display_name",
            "phone", "email", "wilaya", "address",
            "full_name", "birth_date", "gender", "education_level",
            "company_name", "trade_register_number", "sector",
            "responsible_name", "responsible_position",
            "source", "created_at", "updated_at",
            "participants", "enrollments",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs):
        client_type = attrs.get("client_type", getattr(self.instance, "client_type", "individual"))
        if client_type == "individual" and not attrs.get("full_name", getattr(self.instance, "full_name", "")):
            raise serializers.ValidationError({"full_name": "الاسم الكامل مطلوب بالنسبة للأفراد."})
        if client_type == "enterprise" and not attrs.get("company_name", getattr(self.instance, "company_name", "")):
            raise serializers.ValidationError({"company_name": "اسم المؤسسة مطلوب بالنسبة للمؤسسات."})
        return attrs


# ---------------------------------------------------------------------------
# Public registration (write-only) — creates Client + Participant(s) + Enrollment(s)
# in a single call. Two flavours: an individual signing up alone, or an
# enterprise booking a batch of its own employees onto one or more offerings.
# ---------------------------------------------------------------------------


class IndividualRegistrationSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    phone = serializers.RegexField(
        r"^0(5|6|7)\d{8}$", error_messages={"invalid": "رقم هاتف جزائري غير صالح، مثال: 0770123456"},
    )
    email = serializers.EmailField(required=False, allow_blank=True)
    birth_date = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(choices=GENDER_CHOICES, required=False, allow_blank=True)
    education_level = serializers.CharField(required=False, allow_blank=True, max_length=100)
    wilaya = serializers.CharField(required=False, allow_blank=True, max_length=60, default="سطيف")
    motivation = serializers.CharField(required=False, allow_blank=True)
    source = serializers.ChoiceField(choices=SOURCE_CHOICES, required=False, default="web")
    offering_codes = serializers.ListField(
        child=serializers.CharField(), allow_empty=False,
        help_text="قائمة برموز التخصصات المطلوبة، مثال: [\"TAG0701\"]",
    )
    # Honeypot: real clients never fill this; any bot that fills every field gets rejected.
    website = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate_website(self, value):
        if value:
            raise serializers.ValidationError("تعذر إرسال الطلب.")
        return value

    def validate_offering_codes(self, codes):
        offerings = list(Offering.objects.filter(code__in=codes, is_active=True))
        missing = set(codes) - {o.code for o in offerings}
        if missing:
            raise serializers.ValidationError(f"تخصصات غير موجودة أو غير نشطة: {', '.join(sorted(missing))}")
        self._offerings = offerings
        return codes

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop("website", None)
        validated_data.pop("offering_codes")
        motivation = validated_data.pop("motivation", "")
        source = validated_data.pop("source", "web")

        client = Client.objects.create(
            client_type="individual",
            phone=validated_data["phone"],
            email=validated_data.get("email", ""),
            wilaya=validated_data.get("wilaya") or "سطيف",
            full_name=validated_data["full_name"],
            birth_date=validated_data.get("birth_date"),
            gender=validated_data.get("gender", ""),
            education_level=validated_data.get("education_level", ""),
            source=source,
        )
        participant = Participant.objects.create(
            client=client,
            full_name=client.full_name,
            phone=client.phone,
            email=client.email,
            birth_date=client.birth_date,
            gender=client.gender,
            education_level=client.education_level,
        )
        enrollments = [
            Enrollment(client=client, participant=participant, offering=o, motivation=motivation)
            for o in self._offerings
        ]
        Enrollment.objects.bulk_create(enrollments)
        return {"client": client, "enrollments": Enrollment.objects.filter(client=client)}

    def to_representation(self, instance):
        return {
            "client": ClientSerializer(instance["client"]).data,
            "enrollments": EnrollmentSerializer(instance["enrollments"], many=True).data,
        }


class EnterpriseParticipantInputSerializer(serializers.Serializer):
    """One employee within an enterprise's batch registration payload."""

    full_name = serializers.CharField(max_length=150)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    email = serializers.EmailField(required=False, allow_blank=True)
    birth_date = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(choices=GENDER_CHOICES, required=False, allow_blank=True)
    education_level = serializers.CharField(required=False, allow_blank=True, max_length=100)
    position = serializers.CharField(required=False, allow_blank=True, max_length=100)


class EnterpriseRegistrationSerializer(serializers.Serializer):
    company_name = serializers.CharField(max_length=200)
    trade_register_number = serializers.CharField(required=False, allow_blank=True, max_length=60)
    sector = serializers.CharField(required=False, allow_blank=True, max_length=120)
    responsible_name = serializers.CharField(max_length=150)
    responsible_position = serializers.CharField(required=False, allow_blank=True, max_length=100)
    phone = serializers.RegexField(
        r"^0(5|6|7)\d{8}$", error_messages={"invalid": "رقم هاتف جزائري غير صالح، مثال: 0770123456"},
    )
    email = serializers.EmailField(required=False, allow_blank=True)
    wilaya = serializers.CharField(required=False, allow_blank=True, max_length=60, default="سطيف")
    address = serializers.CharField(required=False, allow_blank=True, max_length=255)
    motivation = serializers.CharField(required=False, allow_blank=True)
    source = serializers.ChoiceField(choices=SOURCE_CHOICES, required=False, default="web")
    offering_codes = serializers.ListField(
        child=serializers.CharField(), allow_empty=False,
        help_text="رموز التخصصات المطلوبة لكل المشاركين المذكورين أدناه.",
    )
    participants = EnterpriseParticipantInputSerializer(many=True, allow_empty=False)
    website = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate_website(self, value):
        if value:
            raise serializers.ValidationError("تعذر إرسال الطلب.")
        return value

    def validate_offering_codes(self, codes):
        offerings = list(Offering.objects.filter(code__in=codes, is_active=True))
        missing = set(codes) - {o.code for o in offerings}
        if missing:
            raise serializers.ValidationError(f"تخصصات غير موجودة أو غير نشطة: {', '.join(sorted(missing))}")
        self._offerings = offerings
        return codes

    def validate_participants(self, participants):
        if len(participants) > 200:
            raise serializers.ValidationError("عدد المشاركين كبير جدا في طلب واحد (الحد الأقصى 200).")
        return participants

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop("website", None)
        validated_data.pop("offering_codes")
        participants_data = validated_data.pop("participants")
        motivation = validated_data.pop("motivation", "")
        source = validated_data.pop("source", "web")

        client = Client.objects.create(
            client_type="enterprise",
            phone=validated_data["phone"],
            email=validated_data.get("email", ""),
            wilaya=validated_data.get("wilaya") or "سطيف",
            address=validated_data.get("address", ""),
            company_name=validated_data["company_name"],
            trade_register_number=validated_data.get("trade_register_number", ""),
            sector=validated_data.get("sector", ""),
            responsible_name=validated_data["responsible_name"],
            responsible_position=validated_data.get("responsible_position", ""),
            source=source,
        )

        participants = [
            Participant.objects.create(client=client, **p) for p in participants_data
        ]

        enrollments = [
            Enrollment(client=client, participant=participant, offering=offering, motivation=motivation)
            for participant in participants
            for offering in self._offerings
        ]
        Enrollment.objects.bulk_create(enrollments)

        return {"client": client, "enrollments": Enrollment.objects.filter(client=client)}

    def to_representation(self, instance):
        return {
            "client": ClientSerializer(instance["client"]).data,
            "enrollments": EnrollmentSerializer(instance["enrollments"], many=True).data,
        }
