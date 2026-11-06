"""Automatic audit entries, login lockout and notifications (Design 4.8.1, 4.8.4, FR-17)."""

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.urls import NoReverseMatch, reverse

from employees.models import Employee
from leave.models import LeaveRequest

from . import lockout
from .audit import log_action
from .models import AuditLog, User
from .notifications import notify

# Saves that only touch these fields are bookkeeping, not changes worth auditing.
QUIET_USER_FIELDS = {"last_login", "failed_login_attempts", "locked_until", "password", "updated_at"}


def _url(name, *args):
    try:
        return reverse(name, args=args)
    except NoReverseMatch:
        return ""


# ------------------------------------------------------------------ logins
@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    lockout.record_success(user)
    log_action(AuditLog.Action.LOGIN, f"{user.username} logged in", user=user, request=request)


@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    if user is not None:
        log_action(AuditLog.Action.LOGOUT, f"{user.username} logged out", user=user, request=request)


@receiver(user_login_failed)
def on_login_failed(sender, credentials, request=None, **kwargs):
    attempted = credentials.get("username", "")
    user = lockout.find_user(attempted)
    log_action(
        AuditLog.Action.LOGIN_FAILED,
        f"Failed login for '{attempted[:60]}'",
        user=user,
        request=request,
    )
    if lockout.record_failure(user):
        log_action(
            AuditLog.Action.LOCKED,
            f"{user.username} locked for {lockout.LOCKOUT_MINUTES} minutes after "
            f"{lockout.MAX_FAILED_ATTEMPTS} failed attempts",
            user=user,
            request=request,
        )


# ------------------------------------------------------------ user accounts
@receiver(pre_save, sender=User)
def remember_user(sender, instance, **kwargs):
    old = User.objects.filter(pk=instance.pk).values("role_id", "is_active").first()
    instance._old = old


@receiver(post_save, sender=User)
def audit_user(sender, instance, created, update_fields=None, **kwargs):
    if update_fields and set(update_fields) <= QUIET_USER_FIELDS:
        return
    if created:
        log_action(
            AuditLog.Action.CREATE,
            f"Created user account {instance.username} ({instance.role.role_name})",
            record=instance,
        )
        return
    old = getattr(instance, "_old", None) or {}
    if old.get("role_id") and old["role_id"] != instance.role_id:
        from .models import Role

        before = Role.objects.filter(pk=old["role_id"]).values_list("role_name", flat=True).first()
        log_action(
            AuditLog.Action.ROLE_CHANGE,
            f"Changed {instance.username}'s role from {before} to {instance.role.role_name}",
            record=instance,
        )
    if "is_active" in old and old["is_active"] != instance.is_active:
        action = AuditLog.Action.ACTIVATE if instance.is_active else AuditLog.Action.DEACTIVATE
        log_action(action, f"{action} user account {instance.username}", record=instance)


# ---------------------------------------------------------------- employees
@receiver(pre_save, sender=Employee)
def remember_employee(sender, instance, **kwargs):
    instance._old_status = (
        Employee.objects.filter(pk=instance.pk).values_list("employment_status", flat=True).first()
    )


@receiver(post_save, sender=Employee)
def audit_employee(sender, instance, created, **kwargs):
    name = f"{instance.first_name} {instance.last_name} ({instance.employee_number})"
    if created:
        log_action(AuditLog.Action.CREATE, f"Added employee {name}", record=instance)
        return
    old = getattr(instance, "_old_status", None)
    if old != instance.employment_status and "Inactive" in (old, instance.employment_status):
        action = (
            AuditLog.Action.DEACTIVATE
            if instance.employment_status == "Inactive"
            else AuditLog.Action.ACTIVATE
        )
        log_action(action, f"{action} employee {name}", record=instance)
    else:
        log_action(AuditLog.Action.UPDATE, f"Updated employee {name}", record=instance)


# -------------------------------------------------------------------- leave
@receiver(pre_save, sender=LeaveRequest)
def remember_leave(sender, instance, **kwargs):
    instance._old_status = (
        LeaveRequest.objects.filter(pk=instance.pk).values_list("status", flat=True).first()
    )


def _approvers_for(leave_request):
    """Managers of the employee's department; HR Officers when the employee is that manager."""
    employee = leave_request.employee
    managers = User.objects.filter(
        is_active=True,
        role__role_name="Manager",
        employee__department_id=employee.department_id,
    ).exclude(employee=employee)
    if managers.exists():
        return managers
    return User.objects.filter(is_active=True, role__role_name="HR Officer").exclude(
        employee=employee
    )


@receiver(post_save, sender=LeaveRequest)
def leave_events(sender, instance, created, **kwargs):
    employee = instance.employee
    who = f"{employee.first_name} {employee.last_name}"
    period = f"{instance.start_date:%d %b} to {instance.end_date:%d %b %Y}"

    if created and instance.status == LeaveRequest.Status.PENDING:
        for approver in _approvers_for(instance):
            notify(
                approver,
                f"{who} requested {instance.leave_type.lower()} leave, {period}.",
                _url("leave:review", instance.pk),
            )
        return

    old = getattr(instance, "_old_status", None)
    if old == LeaveRequest.Status.PENDING and instance.status in (
        LeaveRequest.Status.APPROVED,
        LeaveRequest.Status.REJECTED,
    ):
        decision = instance.status.lower()
        log_action(
            AuditLog.Action.LEAVE_DECISION,
            f"{decision.title()} {who}'s {instance.leave_type.lower()} leave, {period}",
            record=instance,
        )
        notify(
            getattr(employee, "user_account", None),
            f"Your {instance.leave_type.lower()} leave for {period} was {decision}.",
            _url("leave:home"),
        )
