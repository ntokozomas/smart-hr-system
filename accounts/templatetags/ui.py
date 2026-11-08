"""Shared UI template tags (Design 4.7.3, 4.7.4).

    {% load ui %}
    {% status_badge leave.status %}
"""

from django import template

register = template.Library()

# One colour per meaning everywhere (4.7.3): green = done, amber = waiting, red = stopped.
GOOD = {"Approved", "Completed", "Hired", "Active", "Present", "Open", "Offer"}
WAITING = {
    "Pending", "Received", "Screening", "Interview", "In Progress",
    "Onboarding", "On Leave", "Late",
}
BAD = {"Rejected", "Cancelled", "Inactive", "Closed", "Absent", "Overdue", "Conflict", "Locked"}


@register.filter
def status_class(value):
    """CSS class for a status value: ok, pend, rej or neutral."""
    value = str(value)
    if value in GOOD:
        return "ok"
    if value in WAITING:
        return "pend"
    if value in BAD:
        return "rej"
    return "neutral"


@register.inclusion_tag("partials/status_badge.html")
def status_badge(value, label=None):
    """Render a colour-coded status pill."""
    return {"value": value, "label": label or value, "css": status_class(value)}


@register.filter
def initials(user):
    """Two-letter initials for the avatar in the top bar."""
    first = (user.first_name or user.username or "?")[:1]
    last = (user.last_name or "")[:1]
    return f"{first}{last}".upper()
