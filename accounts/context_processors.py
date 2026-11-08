"""Template context shared by every page: role, permissions and the sidebar (FR-05)."""

from django.conf import settings
from django.urls import NoReverseMatch, reverse

from .menu import MENU
from .permissions import has_any_permission, permission_codes, role_name

def _is_active(request, url_name):
    match = getattr(request, "resolver_match", None)
    if match is None:
        return False
    
    return match.view_name == url_name

def _mark_active(request, groups):
    """Highlight the menu item for the current page: the item whose address is the
    longest match for the current address (so /leave/apply/ highlights Leave)."""
    path = request.path
    best, best_len = None, 0
    for group in groups:
        for item in group["items"]:
            url = item["url"]
            if not url:
                continue
            matches = path == url or (url != "/" and path.startswith(url))
            if matches and len(url) > best_len:
                best, best_len = item, len(url)
    if best is not None:
        best["active"] = True



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
            visible.append({"label": label, "url": url, "active": False})
        if visible:
            groups.append({"label": group_label, "items": visible})
    _mark_active(request, groups)
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
        profile_url = reverse("employees:my_profile")
    except NoReverseMatch:
        profile_url = None
    unread = user.notifications.filter(is_read=False)
    return {
        "unread_count": unread.count(),
        "recent_notifications": user.notifications.all()[:5],
        "user_role": role_name(user) or ("Superuser" if user.is_superuser else ""),
        "smart_perms": permission_codes(user),
        "menu_groups": visible_menu(request),
        "search_url": search_url,
        "profile_url": profile_url,
    }
