from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("configuration", "0002_remove_appsetting_primary_color"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="appsetting",
            name="allow_self_registration",
        ),
    ]
