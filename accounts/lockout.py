"""Login lockout (Design 4.8.1): 5 failed attempts lock an account for 15 minutes."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def find_user(login):
    """The account matching a username or email, or None."""
    if not login:
        return None
    User = get_user_model()
    matches = User._default_manager.filter(Q(username__iexact=login) | Q(email__iexact=login))
    return matches.first() if matches.count() == 1 else None


def is_locked(user):
    return bool(user and user.locked_until and user.locked_until > timezone.now())


def minutes_left(user):
    seconds = (user.locked_until - timezone.now()).total_seconds()
    return max(1, int(seconds // 60) + (1 if seconds % 60 else 0))


def record_failure(user):
    """Count a failed attempt. Returns True when this attempt locked the account."""
    if user is None or is_locked(user):
        return False
    user.failed_login_attempts += 1
    locked_now = user.failed_login_attempts >= MAX_FAILED_ATTEMPTS
    if locked_now:
        user.locked_until = timezone.now() + timedelta(minutes=LOCKOUT_MINUTES)
        user.failed_login_attempts = 0
    user.save(update_fields=["failed_login_attempts", "locked_until"])
    return locked_now


def record_success(user):
    if user.failed_login_attempts or user.locked_until:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save(update_fields=["failed_login_attempts", "locked_until"])
