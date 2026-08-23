from django import template

register = template.Library()

STATUS_COLORS = {
    "pending": "#c9a227",
    "contacted": "#3b82f6",
    "accepted": "#2ea043",
    "confirmed": "#0f766e",
    "waitlisted": "#8b949e",
    "rejected": "#f85149",
    "cancelled": "#94a3b8",
}


@register.filter
def status_color(status):
    return STATUS_COLORS.get(status, "#8b949e")


@register.filter
def da(value):
    """Format a number as Algerian dinar, e.g. 120000 -> '120 000 دج'."""
    if value in (None, ""):
        return ""
    return f"{int(value):,} دج".replace(",", " ")
