import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("community", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PushNotificationDevice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("device_token", models.TextField(unique=True)),
                ("device_type", models.CharField(choices=[("android", "Android"), ("ios", "iOS"), ("web", "Web Browser")], default="web", max_length=10)),
                ("device_name", models.CharField(blank=True, max_length=200)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("last_used", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="devices", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-last_used"],
                "unique_together": {("user", "device_token")},
            },
        ),
    ]
