from django import template
from django.utils.html import format_html

register = template.Library()

STATUS_COLORS = {
    "pending": "#c9a227",
    "contacted": "#3b82f6",
    "accepted": "#2ea043",
    "confirmed": "#0f766e",
    "waitlisted": "#8b949e",
    "rejected": "#f85149",
    "cancelled": "#94a3b8",
    "priced": "#3b82f6",
    "approved": "#2ea043",
}


@register.filter
def status_color(status):
    return STATUS_COLORS.get(status, "#8b949e")


@register.filter
def da(value):
    """Format a number as Algerian dinar, e.g. 120000 -> '120 000 دج'.

    Wrapped in a <bdi dir="ltr"> isolate so the digit groups and the
    currency suffix always render left-to-right in their correct order,
    regardless of the surrounding RTL context (without this, the Unicode
    bidi algorithm can reorder the space-separated thousand groups when
    the value sits inside RTL text/tables).
    """
    if value in (None, ""):
        return ""
    formatted = f"{int(value):,} دج".replace(",", " ")
    return format_html('<bdi dir="ltr">{}</bdi>', formatted)