from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import random

from community.models import CustomUser, Community, AlertCategory, Alert


class Command(BaseCommand):
    help = 'Create sample data for the community alert system'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')
        
        # Create communities
        communities_data = [
            {
                'name': 'Downtown District',
                'description': 'Central business and residential area',
                'latitude': Decimal('40.7589'),
                'longitude': Decimal('-73.9851'),
                'radius_km': 2.5
            },
            {
                'name': 'Riverside Neighborhood',
                'description': 'Quiet residential area by the river',
                'latitude': Decimal('40.7614'),
                'longitude': Decimal('-73.9776'),
                'radius_km': 1.8
            },
            {
                'name': 'University Area',
                'description': 'Student housing and campus vicinity',
                'latitude': Decimal('40.7505'),
                'longitude': Decimal('-73.9934'),
                'radius_km': 2.0
            }
        ]
        
        communities = []
        for data in communities_data:
            community, created = Community.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            communities.append(community)
            if created:
                self.stdout.write(f'Created community: {community.name}')
        
        # Create alert categories
        categories_data = [
            {
                'name': 'Theft',
                'description': 'Property theft, burglary, shoplifting',
                'icon': 'fas fa-user-secret',
                'color': '#dc3545'
            },
            {
                'name': 'Suspicious Activity',
                'description': 'Suspicious people or behavior',
                'icon': 'fas fa-eye',
                'color': '#ffc107'
            },
            {
                'name': 'Vandalism',
                'description': 'Property damage, graffiti',
                'icon': 'fas fa-hammer',
                'color': '#fd7e14'
            },
            {
                'name': 'Emergency',
                'description': 'Medical emergency, fire, accident',
                'icon': 'fas fa-ambulance',
                'color': '#dc3545'
            },
            {
                'name': 'Traffic Incident',
                'description': 'Road accidents, traffic issues',
                'icon': 'fas fa-car-crash',
                'color': '#17a2b8'
            },
            {
                'name': 'Noise Complaint',
                'description': 'Loud noise, disturbances',
                'icon': 'fas fa-volume-up',
                'color': '#6f42c1'
            }
        ]
        
        categories = []
        for data in categories_data:
            category, created = AlertCategory.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            categories.append(category)
            if created:
                self.stdout.write(f'Created category: {category.name}')
        
        # Create a sample admin user
        admin_user, created = CustomUser.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'role': 'admin',
                'first_name': 'System',
                'last_name': 'Administrator',
                'latitude': Decimal('40.7589'),
                'longitude': Decimal('-73.9851'),
                'email_verified': True
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            admin_user.communities.add(*communities)
            self.stdout.write('Created admin user (username: admin, password: admin123)')
        
        # Create sample community members
        sample_users_data = [
            {
                'username': 'john_doe',
                'email': 'john@example.com',
                'first_name': 'John',
                'last_name': 'Doe',
                'latitude': Decimal('40.7600'),
                'longitude': Decimal('-73.9800')
            },
            {
                'username': 'jane_smith',
                'email': 'jane@example.com',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'latitude': Decimal('40.7620'),
                'longitude': Decimal('-73.9760')
            },
            {
                'username': 'mike_wilson',
                'email': 'mike@example.com',
                'first_name': 'Mike',
                'last_name': 'Wilson',
                'latitude': Decimal('40.7510'),
                'longitude': Decimal('-73.9940')
            }
        ]
        
        users = [admin_user]
        for data in sample_users_data:
            user, created = CustomUser.objects.get_or_create(
                username=data['username'],
                defaults={**data, 'email_verified': True}
            )
            if created:
                user.set_password('password123')
                user.save()
                user.communities.add(random.choice(communities))
                self.stdout.write(f'Created user: {user.username}')
            users.append(user)
        
        # Create sample alerts
        sample_alerts_data = [
            {
                'title': 'Bike stolen from apartment complex',
                'description': 'Blue mountain bike stolen from the bike rack at Oak Street Apartments. Lock was cut. Please keep an eye out for it.',
                'severity': 'medium',
                'status': 'active',
                'address': '123 Oak Street',
                'latitude': Decimal('40.7595'),
                'longitude': Decimal('-73.9845')
            },
            {
                'title': 'Suspicious person near school',
                'description': 'Individual seen loitering near Riverside Elementary School during pickup time. Approached several children but left when confronted.',
                'severity': 'high',
                'status': 'under_review',
                'address': 'Riverside Elementary School',
                'latitude': Decimal('40.7610'),
                'longitude': Decimal('-73.9770')
            },
            {
                'title': 'Car break-in on Main Street',
                'description': 'Multiple cars had windows smashed overnight. Items stolen from vehicles. Police report filed.',
                'severity': 'high',
                'status': 'active',
                'address': 'Main Street parking area',
                'latitude': Decimal('40.7580'),
                'longitude': Decimal('-73.9860')
            },
            {
                'title': 'Loud party disturbance',
                'description': 'Ongoing loud party with music and shouting. Started around 11 PM and still going.',
                'severity': 'low',
                'status': 'resolved',
                'address': '456 University Avenue',
                'latitude': Decimal('40.7500'),
                'longitude': Decimal('-73.9930')
            },
            {
                'title': 'Medical emergency resolved',
                'description': 'Elderly resident had a fall, ambulance called and person taken to hospital. All clear now.',
                'severity': 'critical',
                'status': 'resolved',
                'address': 'Riverside Park',
                'latitude': Decimal('40.7625'),
                'longitude': Decimal('-73.9755')
            }
        ]
        
        for alert_data in sample_alerts_data:
            # Assign random category and community based on location
            category = random.choice(categories)
            if 'stolen' in alert_data['title'].lower() or 'break-in' in alert_data['title'].lower():
                category = AlertCategory.objects.get(name='Theft')
            elif 'suspicious' in alert_data['title'].lower():
                category = AlertCategory.objects.get(name='Suspicious Activity')
            elif 'emergency' in alert_data['title'].lower():
                category = AlertCategory.objects.get(name='Emergency')
            elif 'party' in alert_data['title'].lower() or 'loud' in alert_data['title'].lower():
                category = AlertCategory.objects.get(name='Noise Complaint')
            
            # Find closest community
            community = communities[0]  # Default to first community
            alert_lat = float(alert_data['latitude'])
            alert_lng = float(alert_data['longitude'])
            
            min_distance = float('inf')
            for comm in communities:
                comm_lat = float(comm.latitude)
                comm_lng = float(comm.longitude)
                distance = ((alert_lat - comm_lat) ** 2 + (alert_lng - comm_lng) ** 2) ** 0.5
                if distance < min_distance:
                    min_distance = distance
                    community = comm
            
            alert, created = Alert.objects.get_or_create(
                title=alert_data['title'],
                defaults={
                    **alert_data,
                    'category': category,
                    'community': community,
                    'created_by': random.choice(users),
                    'incident_datetime': timezone.now() - timedelta(hours=random.randint(1, 72)),
                    'view_count': random.randint(5, 50),
                    'upvotes': random.randint(0, 15),
                    'downvotes': random.randint(0, 3)
                }
            )
            if created:
                self.stdout.write(f'Created alert: {alert.title}')
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created sample data!')
        )
        self.stdout.write('You can now login with:')
        self.stdout.write('  Username: admin')
        self.stdout.write('  Password: admin123')
        self.stdout.write('')
        self.stdout.write('Or create new accounts using the registration form.')