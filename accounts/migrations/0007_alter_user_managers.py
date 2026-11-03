from django.db import migrations

import accounts.models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0006_user_created_at_user_updated_at"),
    ]

    operations = [
        migrations.AlterModelManagers(
            name="user",
            managers=[
                ("objects", accounts.models.SmartHRUserManager()),
            ],
        ),
    ]
