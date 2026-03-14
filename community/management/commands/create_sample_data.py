from datetime import timedelta

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from community.models import (
    Alert,
    AlertCategory,
    AlertComment,
    AlertMedia,
    AlertVote,
    Community,
    CustomUser,
    Notification,
    PushNotificationDevice,
)


class Command(BaseCommand):
    help = "Reset alert data and populate sample records for all community models"

    def handle(self, *args, **options):
        self.stdout.write("Resetting alert data and populating sample records...")

        with transaction.atomic():
            users = self._create_users()
            communities = self._create_communities(users)
            categories = self._create_categories()
            alerts = self._reset_and_create_alerts(users, communities, categories)
            self._create_alert_engagement(users, alerts)
            self._create_notifications(users, alerts)
            self._create_devices(users)

        self.stdout.write(self.style.SUCCESS("Database sample data created successfully."))
        self.stdout.write("Admin login:")
        self.stdout.write("  Email: admin@example.com")
        self.stdout.write("  Password: admin123")

    def _create_users(self):
        users_data = [
            {
                "username": "admin",
                "email": "admin@example.com",
                "password": "admin123",
                "role": "admin",
                "first_name": "System",
                "last_name": "Administrator",
                "is_staff": True,
                "is_superuser": True,
            },
            {
                "username": "amina_mod",
                "email": "amina@example.com",
                "password": "password123",
                "role": "moderator",
                "first_name": "Amina",
                "last_name": "Balogun",
                "is_staff": True,
                "is_superuser": False,
            },
            {
                "username": "john_doe",
                "email": "john@example.com",
                "password": "password123",
                "role": "member",
                "first_name": "John",
                "last_name": "Doe",
                "is_staff": False,
                "is_superuser": False,
            },
            {
                "username": "jane_smith",
                "email": "jane@example.com",
                "password": "password123",
                "role": "member",
                "first_name": "Jane",
                "last_name": "Smith",
                "is_staff": False,
                "is_superuser": False,
            },
            {
                "username": "mike_wilson",
                "email": "mike@example.com",
                "password": "password123",
                "role": "member",
                "first_name": "Mike",
                "last_name": "Wilson",
                "is_staff": False,
                "is_superuser": False,
            },
        ]

        users = {}
        for data in users_data:
            password = data.pop("password")
            user, _ = CustomUser.objects.update_or_create(
                email=data["email"],
                defaults={
                    **data,
                    "email_verified": True,
                    "email_notifications": True,
                    "push_notifications": True,
                },
            )
            user.set_password(password)
            user.save()
            users[user.username] = user
            self.stdout.write(f"Upserted user: {user.email}")

        return users

    def _create_communities(self, users):
        community_specs = [
            {
                "name": "Downtown District",
                "description": "Central business and residential area with frequent commuter traffic.",
                "created_by": users["admin"],
                "members": ["admin", "amina_mod", "john_doe", "jane_smith"],
            },
            {
                "name": "Riverside Neighborhood",
                "description": "Mixed residential zone near the riverfront parks and schools.",
                "created_by": users["amina_mod"],
                "members": ["admin", "amina_mod", "jane_smith", "mike_wilson"],
            },
            {
                "name": "University Area",
                "description": "Campus-adjacent housing, hostels, cafes, and student services.",
                "created_by": users["admin"],
                "members": ["admin", "john_doe", "mike_wilson"],
            },
        ]

        communities = {}
        for spec in community_specs:
            members = spec.pop("members")
            community, _ = Community.objects.update_or_create(
                name=spec["name"],
                defaults=spec,
            )
            community.members.set([users[username] for username in members])
            communities[community.name] = community
            self.stdout.write(f"Upserted community: {community.name}")

        return communities

    def _create_categories(self):
        categories_data = [
            {
                "name": "Theft",
                "description": "Property theft, burglary, and stolen belongings.",
                "icon": "fas fa-user-secret",
                "color": "#dc3545",
            },
            {
                "name": "Suspicious Activity",
                "description": "Unusual behavior, loitering, or attempted intrusion.",
                "icon": "fas fa-eye",
                "color": "#ffc107",
            },
            {
                "name": "Vandalism",
                "description": "Property damage, graffiti, or deliberate destruction.",
                "icon": "fas fa-hammer",
                "color": "#fd7e14",
            },
            {
                "name": "Emergency",
                "description": "Urgent medical, fire, or life-threatening incidents.",
                "icon": "fas fa-ambulance",
                "color": "#c82333",
            },
            {
                "name": "Traffic Incident",
                "description": "Road accidents, obstructions, and traffic hazards.",
                "icon": "fas fa-car-crash",
                "color": "#17a2b8",
            },
            {
                "name": "Noise Complaint",
                "description": "Repeated loud disturbances affecting residents.",
                "icon": "fas fa-volume-up",
                "color": "#6f42c1",
            },
        ]

        categories = {}
        for data in categories_data:
            category, _ = AlertCategory.objects.update_or_create(
                name=data["name"],
                defaults=data,
            )
            categories[category.name] = category
            self.stdout.write(f"Upserted category: {category.name}")

        return categories

    def _reset_and_create_alerts(self, users, communities, categories):
        deleted_alerts = Alert.objects.count()
        Alert.objects.all().delete()
        self.stdout.write(f"Deleted {deleted_alerts} existing alerts.")

        now = timezone.now()
        alert_specs = [
            {
                "title": "Phone snatching reported at evening bus stop",
                "description": "Residents reported two riders snatching a commuter's phone near the main bus stop. Witnesses said the riders headed toward Market Road.",
                "category": categories["Theft"],
                "severity": "high",
                "status": "active",
                "community": communities["Downtown District"],
                "address": "12 Market Road Bus Stop",
                "created_by": users["john_doe"],
                "updated_by": users["amina_mod"],
                "incident_datetime": now - timedelta(hours=2),
                "view_count": 48,
                "upvotes": 3,
                "downvotes": 0,
                "is_public": True,
                "is_verified": True,
            },
            {
                "title": "Unidentified van circling school perimeter",
                "description": "A white van was seen making repeated slow passes around the school perimeter during dismissal. Security was notified and reviewing camera footage.",
                "category": categories["Suspicious Activity"],
                "severity": "critical",
                "status": "under_review",
                "community": communities["Riverside Neighborhood"],
                "address": "Riverside Community School Gate",
                "created_by": users["jane_smith"],
                "updated_by": users["amina_mod"],
                "incident_datetime": now - timedelta(hours=5),
                "view_count": 72,
                "upvotes": 2,
                "downvotes": 0,
                "is_public": True,
                "is_verified": True,
            },
            {
                "title": "Water tanker blocking emergency lane",
                "description": "A broken-down tanker blocked the narrow access lane behind the clinic, causing heavy congestion for over an hour before being moved.",
                "category": categories["Traffic Incident"],
                "severity": "medium",
                "status": "resolved",
                "community": communities["University Area"],
                "address": "Clinic Service Lane, University Area",
                "created_by": users["mike_wilson"],
                "updated_by": users["admin"],
                "incident_datetime": now - timedelta(days=1, hours=3),
                "resolved_at": now - timedelta(days=1, hours=1),
                "view_count": 27,
                "upvotes": 1,
                "downvotes": 0,
                "is_public": True,
                "is_verified": False,
            },
            {
                "title": "Generator noise disturbance after midnight",
                "description": "Multiple apartments reported persistent generator noise and shouting from a courtyard after midnight. The issue was resolved after landlord intervention.",
                "category": categories["Noise Complaint"],
                "severity": "low",
                "status": "resolved",
                "community": communities["Downtown District"],
                "address": "4 Unity Close",
                "created_by": users["john_doe"],
                "updated_by": users["amina_mod"],
                "incident_datetime": now - timedelta(days=2, hours=4),
                "resolved_at": now - timedelta(days=2, hours=2),
                "view_count": 19,
                "upvotes": 0,
                "downvotes": 1,
                "is_public": True,
                "is_verified": False,
            },
        ]

        alerts = []
        for spec in alert_specs:
            alert = Alert.objects.create(**spec)
            alerts.append(alert)
            self.stdout.write(f"Created alert: {alert.title}")

        media_payloads = [
            (alerts[0], "image", "bus_stop_scene.jpg", "Street view captured by nearby shop."),
            (alerts[1], "video", "school_gate_clip.mp4", "Short clip from a resident overlooking the gate."),
        ]
        for alert, media_type, filename, caption in media_payloads:
            media = AlertMedia(alert=alert, media_type=media_type, caption=caption)
            media.file.save(filename, ContentFile(b"sample media placeholder"), save=True)
            self.stdout.write(f"Created media for alert: {alert.title}")

        return alerts

    def _create_alert_engagement(self, users, alerts):
        vote_specs = [
            (alerts[0], users["amina_mod"], "up"),
            (alerts[0], users["jane_smith"], "up"),
            (alerts[0], users["mike_wilson"], "up"),
            (alerts[1], users["admin"], "up"),
            (alerts[1], users["john_doe"], "up"),
            (alerts[3], users["jane_smith"], "down"),
        ]
        for alert, user, vote_type in vote_specs:
            AlertVote.objects.update_or_create(
                alert=alert,
                user=user,
                defaults={"vote_type": vote_type},
            )

        comment_specs = [
            {
                "alert": alerts[0],
                "user": users["amina_mod"],
                "content": "Security volunteers have been informed. Share plate numbers if anyone has them.",
            },
            {
                "alert": alerts[1],
                "user": users["admin"],
                "content": "The school has confirmed they are reviewing camera coverage for that time window.",
            },
            {
                "alert": alerts[2],
                "user": users["jane_smith"],
                "content": "Traffic is moving normally again. Access to the clinic is clear.",
            },
        ]

        created_comments = []
        for spec in comment_specs:
            comment = AlertComment.objects.create(**spec)
            created_comments.append(comment)

        AlertComment.objects.create(
            alert=alerts[1],
            user=users["amina_mod"],
            content="Police community desk has been contacted for extra patrols.",
            parent=created_comments[1],
        )

        self.stdout.write("Created votes and comments.")

    def _create_notifications(self, users, alerts):
        now = timezone.now()
        notification_specs = [
            {
                "alert": alerts[0],
                "user": users["jane_smith"],
                "notification_type": "push",
                "status": "delivered",
                "title": alerts[0].title,
                "message": "New theft alert near Downtown District.",
                "sent_at": now - timedelta(hours=2),
                "delivered_at": now - timedelta(hours=2) + timedelta(minutes=1),
                "external_id": "push-1001",
            },
            {
                "alert": alerts[1],
                "user": users["admin"],
                "notification_type": "email",
                "status": "sent",
                "title": alerts[1].title,
                "message": "Suspicious activity alert requires moderation follow-up.",
                "sent_at": now - timedelta(hours=4, minutes=50),
                "external_id": "email-1002",
            },
            {
                "alert": alerts[2],
                "user": users["john_doe"],
                "notification_type": "sms",
                "status": "failed",
                "title": alerts[2].title,
                "message": "Traffic incident update for University Area.",
                "external_id": "sms-1003",
            },
        ]

        for spec in notification_specs:
            Notification.objects.create(**spec)

        self.stdout.write("Created notifications.")

    def _create_devices(self, users):
        device_specs = [
            {
                "user": users["admin"],
                "device_token": "web-token-admin-001",
                "device_type": "web",
                "device_name": "Chrome on Mac",
                "is_active": True,
            },
            {
                "user": users["amina_mod"],
                "device_token": "android-token-amina-001",
                "device_type": "android",
                "device_name": "Pixel 8",
                "is_active": True,
            },
            {
                "user": users["john_doe"],
                "device_token": "ios-token-john-001",
                "device_type": "ios",
                "device_name": "iPhone 14",
                "is_active": True,
            },
        ]

        PushNotificationDevice.objects.all().delete()
        for spec in device_specs:
            PushNotificationDevice.objects.create(**spec)

        self.stdout.write("Created push notification devices.")
