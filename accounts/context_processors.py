"""Template context shared by every page: role, permissions and the sidebar (FR-05)."""

from django.conf import settings
from django.urls import NoReverseMatch, reverse

from .menu import MENU
from .permissions import has_any_permission, permission_codes, role_name


def _is_active(request, url_name):
    match = getattr(request, "resolver_match", None)
    if match is None:
        return False
    if ":" in url_name:
        return match.namespace == url_name.split(":", 1)[0]
    return match.view_name == url_name


def visible_menu(request):
    """Build the sidebar groups the current user may see."""
    user = request.user
    groups = []
    for group_label, items in MENU:
        visible = []
        for label, url_name, codes in items:
            if codes and not has_any_permission(user, *codes):
                continue
            try:
                url = reverse(url_name)
            except NoReverseMatch:
                # Module not built yet: show it greyed out while developing only.
                if settings.DEBUG:
                    visible.append({"label": label, "url": None, "active": False})
                continue
            visible.append(
                {"label": label, "url": url, "active": _is_active(request, url_name)}
            )
        if visible:
            groups.append({"label": group_label, "items": visible})
    return groups


def navigation(request):
    user = request.user
    if not user.is_authenticated:
        return {}
    try:
        search_url = reverse("employees:search")
    except NoReverseMatch:
        search_url = None
    try:
        profile_url = reverse("accounts:profile")
    except NoReverseMatch:
        profile_url = None
    return {
        "user_role": role_name(user) or ("Superuser" if user.is_superuser else ""),
        "smart_perms": permission_codes(user),
        "menu_groups": visible_menu(request),
        "search_url": search_url,
        "profile_url": profile_url,
    }
