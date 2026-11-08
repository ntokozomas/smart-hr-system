"""In-app notifications (FR-17).

    from accounts.notifications import notify
    notify(user, "Your onboarding task is due tomorrow.", link="/lifecycle/")
"""

from .models import Notification


def notify(recipient, message, link=""):
    """Send a notification to one user. Inactive or missing users are skipped."""
    if recipient is None or not recipient.is_active:
        return None
    return Notification.objects.create(recipient=recipient, message=message[:255], link=link)
