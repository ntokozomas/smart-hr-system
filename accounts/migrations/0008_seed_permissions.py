"""Seed module permissions and give them to roles (Design 4.8.2, Table 4.8.1)."""

from django.db import migrations

ADMIN, HR, MANAGER, EMPLOYEE = "Administrator", "HR Officer", "Manager", "Employee"
STAFF = (HR, MANAGER, EMPLOYEE)  # everyone who has an employee record

# (module, code, description, roles)
PERMISSIONS = [
    ("accounts", "accounts.manage_users",
     "Create, edit and deactivate user accounts and assign roles (FR-03, FR-04)", (ADMIN,)),
    ("audit", "audit.view", "View the audit log (4.8.4)", (ADMIN,)),
    ("profile", "profile.view_own", "View own profile (FR-11)", (ADMIN,) + STAFF),
    ("profile", "profile.update_contact",
     "Update own contact details (FR-11)", (ADMIN,) + STAFF),
    ("employees", "employees.view",
     "View employee records; managers see their department only (FR-07 to FR-12, FR-40)",
     (HR, MANAGER)),
    ("employees", "employees.manage",
     "Add, edit and deactivate employees, departments and job positions", (HR,)),
    ("leave", "leave.apply", "Apply for leave and view own requests (FR-14, FR-15)", STAFF),
    ("leave", "leave.view",
     "View leave requests and the leave calendar; managers see their department (FR-19)",
     (HR, MANAGER)),
    ("leave", "leave.approve", "Approve or reject leave requests (FR-17, FR-18)", (HR, MANAGER)),
    ("attendance", "attendance.record_own",
     "Check in, check out and view own attendance (FR-20)", STAFF),
    ("attendance", "attendance.view",
     "View attendance records; managers see their department (FR-21)", (HR, MANAGER)),
    ("recruitment", "recruitment.manage",
     "Manage vacancies, applications and match scores (FR-22 to FR-26)", (HR,)),
    ("lifecycle", "lifecycle.manage",
     "Manage onboarding and employee exits (FR-27 to FR-31)", (HR,)),
    ("performance", "performance.view",
     "View performance records; managers see their department (FR-34)", (HR, MANAGER)),
    ("performance", "performance.manage",
     "Record performance reviews for own department (FR-32)", (MANAGER,)),
    ("performance", "performance.view_own", "View own completed reviews (FR-33)", STAFF),
    ("reports", "reports.view",
     "View dashboards and reports; managers see their department (FR-35 to FR-38)",
     (HR, MANAGER)),
]


def seed_permissions(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    Permission = apps.get_model("accounts", "Permission")
    RolePermission = apps.get_model("accounts", "RolePermission")

    roles = {role.role_name: role for role in Role.objects.all()}
    for module, code, description, role_names in PERMISSIONS:
        permission, _ = Permission.objects.update_or_create(
            permission_name=code,
            defaults={"module": module, "description": description},
        )
        for name in role_names:
            if name in roles:
                RolePermission.objects.get_or_create(role=roles[name], permission=permission)


def remove_permissions(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    Permission.objects.filter(permission_name__in=[p[1] for p in PERMISSIONS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0007_alter_user_managers"),
    ]

    operations = [
        migrations.RunPython(seed_permissions, remove_permissions),
    ]
