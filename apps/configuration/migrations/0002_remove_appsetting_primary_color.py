from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("configuration", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="appsetting",
            name="primary_color",
        ),
    ]
