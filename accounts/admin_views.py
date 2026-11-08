"""Administrator screens and notifications (T13).

- Users and roles (FR-03, FR-04): only the Administrator.
- Audit log (Design 4.8.4): only the Administrator, read-only.
- Notifications (FR-17): every logged-in user sees their own.
"""

from datetime import datetime

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from .admin_forms import NewUserForm, ResetPasswordForm, UserForm
from .audit import log_action
from .models import AuditLog, Notification, Permission, Role, RolePermission, User
from .permissions import require_permission

PAGE_SIZE = 25  # Design 4.7.3


def _page(request, queryset):
    return Paginator(queryset, PAGE_SIZE).get_page(request.GET.get("page"))


# ------------------------------------------------------------------- users
@require_permission("accounts.manage_users")
def user_list(request):
    """FR-03: all accounts, searchable and filtered by role and status."""
    users = User.objects.select_related("role", "employee").order_by("username")
    query = request.GET.get("q", "").strip()
    role = request.GET.get("role", "")
    status = request.GET.get("status", "")
    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
        )
    if role:
        users = users.filter(role__role_name=role)
    if status == "active":
        users = users.filter(is_active=True)
    elif status == "inactive":
        users = users.filter(is_active=False)

    return render(request, "accounts/user_list.html", {
        "page_obj": _page(request, users),
        "roles": Role.objects.order_by("role_name"),
        "query": query,
        "selected_role": role,
        "selected_status": status,
        "now": timezone.now(),
    })


@require_permission("accounts.manage_users")
def user_create(request):
    """FR-03: create an account with exactly one role (FR-04)."""
    form = NewUserForm(request.POST or None, acting_user=request.user)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(request, f"Account {user.username} was created as {user.role.role_name}.")
        return redirect("accounts:users")
    return render(request, "accounts/user_form.html", {"form": form, "title": "Add user"})


@require_permission("accounts.manage_users")
def user_edit(request, pk):
    """FR-03, FR-04: edit details, change the role or the linked employee."""
    account = get_object_or_404(User, pk=pk)
    form = UserForm(request.POST or None, instance=account, acting_user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Account {account.username} was updated.")
        return redirect("accounts:users")
    return render(request, "accounts/user_form.html", {
        "form": form,
        "title": f"Edit {account.username}",
        "account": account,
    })


@require_permission("accounts.manage_users")
def user_toggle_active(request, pk):
    """FR-03: deactivate or reactivate an account. Nothing is deleted."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    account = get_object_or_404(User, pk=pk)
    if account.pk == request.user.pk:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect("accounts:users")
    account.is_active = not account.is_active
    account.save(update_fields=["is_active", "updated_at"])
    state = "reactivated" if account.is_active else "deactivated"
    messages.success(request, f"Account {account.username} was {state}.")
    return redirect("accounts:users")


@require_permission("accounts.manage_users")
def user_reset_password(request, pk):
    """Set a temporary password for a user who forgot theirs; also clears a lockout."""
    account = get_object_or_404(User, pk=pk)
    form = ResetPasswordForm(request.POST or None, user=account)
    if request.method == "POST" and form.is_valid():
        account.set_password(form.cleaned_data["password1"])
        account.failed_login_attempts = 0
        account.locked_until = None
        account.save(update_fields=["password", "failed_login_attempts", "locked_until"])
        log_action(
            AuditLog.Action.PASSWORD_RESET,
            f"Reset the password for {account.username}",
            record=account,
        )
        messages.success(
            request,
            f"The password for {account.username} was reset. Give it to them in person, "
            "and ask them to change it after logging in.",
        )
        return redirect("accounts:users")
    return render(request, "accounts/user_password.html", {"form": form, "account": account})


@require_permission("accounts.manage_users")
def role_matrix(request):
    """Design 4.8.2: which role holds which permission, read-only."""
    roles = list(Role.objects.order_by("role_name"))
    held = set(RolePermission.objects.values_list("role_id", "permission_id"))
    rows = [
        {
            "permission": permission,
            "cells": [(role.pk, permission.pk) in held for role in roles],
        }
        for permission in Permission.objects.order_by("module", "permission_name")
    ]
    return render(request, "accounts/role_matrix.html", {"roles": roles, "rows": rows})


# --------------------------------------------------------------- audit log
def _parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


@require_permission("audit.view")
def audit_log(request):
    """Design 4.8.4: who did what and when. There is no way to edit or delete entries."""
    entries = AuditLog.objects.all()
    action = request.GET.get("action", "")
    query = request.GET.get("q", "").strip()
    date_from = _parse_date(request.GET.get("from"))
    date_to = _parse_date(request.GET.get("to"))
    if action in AuditLog.Action.values:
        entries = entries.filter(action=action)
    if query:
        entries = entries.filter(Q(username__icontains=query) | Q(description__icontains=query))
    if date_from:
        entries = entries.filter(created_at__date__gte=date_from)
    if date_to:
        entries = entries.filter(created_at__date__lte=date_to)

    return render(request, "accounts/audit_log.html", {
        "page_obj": _page(request, entries),
        "actions": AuditLog.Action.choices,
        "selected_action": action,
        "query": query,
        "date_from": request.GET.get("from", ""),
        "date_to": request.GET.get("to", ""),
    })


# ----------------------------------------------------------- notifications
def notification_list(request):
    """FR-17: the user's own notifications, newest first."""
    notes = Notification.objects.filter(recipient=request.user)
    return render(request, "accounts/notifications.html", {"page_obj": _page(request, notes)})


def notification_open(request, pk):
    """Mark one notification as read and go to the page it is about."""
    note = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not note.is_read:
        note.is_read = True
        note.save(update_fields=["is_read"])
    if note.link and url_has_allowed_host_and_scheme(note.link, allowed_hosts={request.get_host()}):
        return redirect(note.link)
    return redirect("accounts:notifications")


def notification_read_all(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    messages.success(request, "All notifications are marked as read.")
    return redirect("accounts:notifications")
