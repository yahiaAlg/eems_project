from django import template

register = template.Library()

_ALGERIAN_MONTHS = {
    1: "جانفي", 2: "فيفري", 3: "مارس", 4: "أفريل", 5: "ماي", 6: "جوان",
    7: "جويلية", 8: "أوت", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر",
}


@register.filter
def dz_month(value):
    """Render a date's month using the Algerian/Maghrebi Arabic month name."""
    if not value:
        return ""
    return _ALGERIAN_MONTHS.get(value.month, "")
