"""Role-based access control helpers (T5, Design 4.8.2, NFR-03).

Every module uses these instead of writing its own checks:

    from accounts.permissions import require_permission, scope_queryset

    @require_permission("leave.approve")
    def approvals(request):
        requests = scope_queryset(LeaveRequest.objects.all(), request.user)
        ...

Hiding a menu item is only a convenience. These checks are the real security:
every view must use one of them, and a failed check returns HTTP 403.
"""

from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.db.models import Q

from .models import Permission

ADMINISTRATOR = "Administrator"
HR_OFFICER = "HR Officer"
MANAGER = "Manager"
EMPLOYEE = "Employee"
ROLES = (ADMINISTRATOR, HR_OFFICER, MANAGER, EMPLOYEE)


def role_name(user):
    """Return the user's role name, or None for anonymous users or users without a role."""
    if not getattr(user, "is_authenticated", False) or not user.role_id:
        return None
    return user.role.role_name


def has_role(user, *roles):
    """True when the user holds one of the given roles. Superusers always pass."""
    if getattr(user, "is_superuser", False) and user.is_active:
        return True
    return role_name(user) in roles


def permission_codes(user):
    """All permission codes the user holds through their role or as extras.

    The result is cached on the user object, so a page makes at most one query.
    """
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return frozenset()
    cached = getattr(user, "_smart_permission_codes", None)
    if cached is None:
        codes = Permission.objects.filter(
            Q(role_permissions__role_id=user.role_id) | Q(user_permissions_extra__user=user)
        ).values_list("permission_name", flat=True)
        cached = frozenset(codes)
        user._smart_permission_codes = cached
    return cached


def has_permission(user, code):
    """True when the user may perform the action, for example ``"leave.approve"``."""
    if getattr(user, "is_superuser", False) and user.is_active:
        return True
    return code in permission_codes(user)


def has_any_permission(user, *codes):
    """True when the user holds at least one of the given permission codes."""
    return any(has_permission(user, code) for code in codes)


def _guard(check):
    """Build a view decorator: anonymous users go to login, others get 403 on failure."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not check(request.user):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


def require_permission(*codes):
    """View decorator: allow the request if the user has any of ``codes`` (NFR-03)."""
    return _guard(lambda user: has_any_permission(user, *codes))


def require_role(*roles):
    """View decorator: allow the request if the user holds one of ``roles``."""
    return _guard(lambda user: has_role(user, *roles))


class RequirePermissionMixin:
    """Class-based view version of ``require_permission``.

    class VacancyList(RequirePermissionMixin, ListView):
        required_permissions = ("recruitment.manage",)
    """

    required_permissions = ()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not has_any_permission(request.user, *self.required_permissions):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


def scope_queryset(queryset, user, employee_field="employee"):
    """Limit records to what the user's role may see (record-level rules, 4.8.2).

    - HR Officers (and superusers) see every record.
    - Managers see records for employees in their own department.
    - Everyone else sees only their own records.
    - A user with no linked employee record sees nothing.

    ``employee_field`` is the path from the model to Employee, for example
    ``"employee"`` for LeaveRequest. Pass ``""`` when the queryset is Employee itself.
    """
    if getattr(user, "is_superuser", False) or has_role(user, HR_OFFICER):
        return queryset

    employee = getattr(user, "employee", None)
    if employee is None:
        return queryset.none()

    prefix = f"{employee_field}__" if employee_field else ""
    if has_role(user, MANAGER):
        return queryset.filter(**{f"{prefix}department_id": employee.department_id})
    return queryset.filter(**{f"{prefix}pk": employee.pk})
