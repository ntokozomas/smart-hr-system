from django.db import migrations


def seed_default_roles(apps, schema_editor):
    """Create the four roles required by the Smart HR specification."""

    Role = apps.get_model("accounts", "Role")
    User = apps.get_model("accounts", "User")

    default_roles = [
        "Administrator",
        "HR Officer",
        "Manager",
        "Employee",
    ]

    # Create roles without duplicating existing records.
    roles = {}

    for role_name in default_roles:
        role, created = Role.objects.get_or_create(
            role_name=role_name,
        )
        roles[role_name] = role

    # Assign a default role to existing accounts that lack one.
    User.objects.filter(
        role__isnull=True,
        is_superuser=True,
    ).update(role=roles["Administrator"])

    User.objects.filter(
        role__isnull=True,
        is_superuser=False,
    ).update(role=roles["Employee"])


def reverse_seed_default_roles(apps, schema_editor):
    """Keep the default roles when reversing this migration.

    Keeping these records avoids accidentally deleting roles
    that may already be referenced by users.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_alter_permission_options_alter_role_options_and_more"),
    ]

    operations = [
        migrations.RunPython(
            seed_default_roles,
            reverse_seed_default_roles,
        ),
    ]
