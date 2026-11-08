"""Audit log helpers (Design 4.8.4).

Most events are recorded automatically (see accounts/signals.py). For anything else,
call log_action from your view, for example when a report is exported:

    from accounts.audit import log_action
    log_action("Export", "Exported the leave report as PDF")
"""

import contextvars

from .models import AuditLog

_current_request = contextvars.ContextVar("current_request", default=None)


class CurrentRequestMiddleware:
    """Remember the current request so model signals can record who made a change."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = _current_request.set(request)
        try:
            return self.get_response(request)
        finally:
            _current_request.reset(token)


def current_request():
    return _current_request.get()


def client_ip(request):
    """The visitor's IP address, using the proxy header when behind Nginx (Design 4.3.3)."""
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")
    return ip or None


def log_action(action, description, record=None, user=None, request=None):
    """Write one audit entry. ``user`` defaults to whoever is logged in for this request."""
    request = request or current_request()
    if user is None and request is not None:
        request_user = getattr(request, "user", None)
        if request_user is not None and request_user.is_authenticated:
            user = request_user
    if user is not None and not getattr(user, "pk", None):
        user = None
    return AuditLog.objects.create(
        user=user,
        username=getattr(user, "username", "") or "",
        action=action,
        record_type=record._meta.verbose_name.title() if record is not None else "",
        record_id=str(record.pk) if record is not None else "",
        description=str(description)[:255],
        ip_address=client_ip(request),
    )
