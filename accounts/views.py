"""Authentication pages, the landing dashboard and the help page (T2, FR-01 to FR-06)."""

from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_not_required
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator

from .context_processors import visible_menu
from .forms import LoginForm, ProfileForm


@method_decorator(login_not_required, name="dispatch")
class LoginView(auth_views.LoginView):
    """FR-01: log in with a username or email address and a password."""

    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    """FR-06: log out. Only accepts POST, so a link on another site cannot log users out."""


class PasswordChangeView(auth_views.PasswordChangeView):
    """FR-06: change password; the new one must pass NFR-06 validation."""

    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:password_change_done")


class PasswordChangeDoneView(auth_views.PasswordChangeDoneView):
    template_name = "accounts/password_change_done.html"


def dashboard(request):
    """Landing page after login (4.7.1).

    Shows shortcuts to the sections the user's role can open. The analytics
    module (T14) adds the HR statistics to this page.
    """
    shortcuts = [
        item
        for group in visible_menu(request)
        for item in group["items"]
        if item["url"] and item["label"] not in ("Dashboard", "Help")
    ]
    return render(request, "dashboard.html", {"shortcuts": shortcuts})


def help_page(request):
    """NFR-17: in-app help page listing what each section is for."""
    return render(request, "help.html")

def my_profile(request):
    """Allow the logged-in user to view and update their own profile."""

    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)

        if form.is_valid():
            form.save()
            return redirect("employees:my_profile")
    else:
        form = ProfileForm(request.POST, instance=request.user)

    return render(
        request,
        "accounts/profile.html",
        {"form": form},
    )