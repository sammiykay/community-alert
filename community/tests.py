from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from .models import Community, AlertCategory, Alert, AlertVote, Notification, AlertComment

User = get_user_model()


class ModelTestCase(TestCase):
    """Test cases for models"""
    
    def setUp(self):
        """Set up test data"""
        self.community = Community.objects.create(
            name="Test Community",
            description="A test community",
            latitude=Decimal('40.7589'),
            longitude=Decimal('-73.9851'),
            radius_km=2.5
        )
        
        self.category = AlertCategory.objects.create(
            name="Test Category",
            description="A test category",
            icon="fas fa-test",
            color="#007bff"
        )
        
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        self.alert = Alert.objects.create(
            title="Test Alert",
            description="This is a test alert",
            category=self.category,
            severity="medium",
            status="active",
            latitude=Decimal('40.7590'),
            longitude=Decimal('-73.9850'),
            address="123 Test Street",
            community=self.community,
            created_by=self.user,
            incident_datetime=timezone.now()
        )
    
    def test_community_creation(self):
        """Test community model creation"""
        self.assertEqual(self.community.name, "Test Community")
        self.assertEqual(str(self.community), "Test Community")
        self.assertTrue(self.community.is_active)
    
    def test_alert_creation(self):
        """Test alert model creation"""
        self.assertEqual(self.alert.title, "Test Alert")
        self.assertEqual(self.alert.severity, "medium")
        self.assertEqual(self.alert.status, "active")
        self.assertEqual(str(self.alert), "Test Alert - medium")
        self.assertFalse(self.alert.is_critical)
    
    def test_alert_is_critical(self):
        """Test alert critical property"""
        critical_alert = Alert.objects.create(
            title="Critical Alert",
            description="This is critical",
            category=self.category,
            severity="critical",
            latitude=Decimal('40.7590'),
            longitude=Decimal('-73.9850'),
            community=self.community,
            created_by=self.user,
            incident_datetime=timezone.now()
        )
        self.assertTrue(critical_alert.is_critical)
    
    def test_custom_user_creation(self):
        """Test custom user model"""
        user = User.objects.create_user(
            username="newuser",
            email="newuser@example.com",
            password="password123",
            role="moderator"
        )
        self.assertEqual(user.role, "moderator")
        self.assertEqual(str(user), "newuser@example.com")
        self.assertTrue(user.email_notifications)
        self.assertEqual(user.notification_radius_km, 5.0)
    
    def test_alert_vote_creation(self):
        """Test alert voting system"""
        vote = AlertVote.objects.create(
            alert=self.alert,
            user=self.user,
            vote_type="up"
        )
        self.assertEqual(vote.vote_type, "up")
        self.assertEqual(vote.alert, self.alert)
        self.assertEqual(vote.user, self.user)


class ViewTestCase(TestCase):
    """Test cases for views"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.community = Community.objects.create(
            name="Test Community",
            latitude=Decimal('40.7589'),
            longitude=Decimal('-73.9851'),
            radius_km=2.5
        )
        
        self.category = AlertCategory.objects.create(
            name="Test Category",
            icon="fas fa-test",
            color="#007bff"
        )
        
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        self.alert = Alert.objects.create(
            title="Test Alert",
            description="This is a test alert",
            category=self.category,
            severity="medium",
            latitude=Decimal('40.7590'),
            longitude=Decimal('-73.9850'),
            community=self.community,
            created_by=self.user,
            incident_datetime=timezone.now()
        )
    
    def test_home_view(self):
        """Test home page view"""
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Community Alert System")
        self.assertContains(response, self.alert.title)
    
    def test_alert_list_view(self):
        """Test alert list view"""
        response = self.client.get(reverse('alert_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.alert.title)
    
    def test_alert_detail_view(self):
        """Test alert detail view"""
        response = self.client.get(reverse('alert_detail', args=[self.alert.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.alert.title)
        self.assertContains(response, self.alert.description)
    
    def test_alert_detail_increments_view_count(self):
        """Test that viewing alert increments view count"""
        initial_count = self.alert.view_count
        self.client.get(reverse('alert_detail', args=[self.alert.id]))
        
        # Refresh from database
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.view_count, initial_count + 1)
    
    def test_login_required_views(self):
        """Test that login-required views redirect when not authenticated"""
        # Test create alert view
        response = self.client.get(reverse('create_alert'))
        self.assertRedirects(response, '/login/?next=/alerts/create/')
        
        # Test edit alert view
        response = self.client.get(reverse('edit_alert', args=[self.alert.id]))
        self.assertRedirects(response, f'/login/?next=/alerts/{self.alert.id}/edit/')
        
        # Test user profile view
        response = self.client.get(reverse('user_profile'))
        self.assertRedirects(response, '/login/?next=/profile/')
    
    def test_authenticated_user_can_create_alert(self):
        """Test that authenticated users can access create alert page"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('create_alert'))
        self.assertEqual(response.status_code, 200)
    
    def test_vote_alert_requires_login(self):
        """Test that voting requires authentication"""
        response = self.client.post(
            reverse('vote_alert', args=[self.alert.id]),
            {'vote_type': 'up'}
        )
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_authenticated_user_can_vote(self):
        """Test that authenticated users can vote on alerts"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('vote_alert', args=[self.alert.id]),
            {'vote_type': 'up'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        
        # Check that vote was created
        vote = AlertVote.objects.get(alert=self.alert, user=self.user)
        self.assertEqual(vote.vote_type, 'up')
    
    def test_user_registration(self):
        """Test user registration"""
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after successful registration
        
        # Check user was created
        user = User.objects.get(username='newuser')
        self.assertEqual(user.email, 'newuser@example.com')
    
    def test_alert_filtering(self):
        """Test alert filtering functionality"""
        # Create another alert with different category
        other_category = AlertCategory.objects.create(
            name="Other Category",
            icon="fas fa-other",
            color="#ff0000"
        )
        
        Alert.objects.create(
            title="Other Alert",
            description="Different alert",
            category=other_category,
            severity="high",
            latitude=Decimal('40.7590'),
            longitude=Decimal('-73.9850'),
            community=self.community,
            created_by=self.user,
            incident_datetime=timezone.now()
        )
        
        # Test category filtering
        response = self.client.get(reverse('alert_list'), {'category': self.category.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Alert")
        self.assertNotContains(response, "Other Alert")
        
        # Test severity filtering
        response = self.client.get(reverse('alert_list'), {'severity': 'high'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Other Alert")
        self.assertNotContains(response, "Test Alert")


class SecurityTestCase(TestCase):
    """Test cases for security measures"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.community = Community.objects.create(
            name="Test Community",
            latitude=Decimal('40.7589'),
            longitude=Decimal('-73.9851'),
            radius_km=2.5
        )
        
        self.category = AlertCategory.objects.create(
            name="Test Category",
            icon="fas fa-test",
            color="#007bff"
        )
        
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        self.other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="testpass123"
        )
        
        self.alert = Alert.objects.create(
            title="Test Alert",
            description="This is a test alert",
            category=self.category,
            severity="medium",
            latitude=Decimal('40.7590'),
            longitude=Decimal('-73.9850'),
            community=self.community,
            created_by=self.user,
            incident_datetime=timezone.now()
        )
    
    def test_user_can_only_edit_own_alerts(self):
        """Test that users can only edit their own alerts"""
        # Login as other user
        self.client.login(username='otheruser', password='testpass123')
        
        # Try to edit alert created by different user
        response = self.client.get(reverse('edit_alert', args=[self.alert.id]))
        self.assertEqual(response.status_code, 302)  # Should redirect
    
    def test_sql_injection_protection(self):
        """Test protection against SQL injection"""
        # Try SQL injection in search parameter
        malicious_search = "'; DROP TABLE community_alert; --"
        response = self.client.get(reverse('alert_list'), {'search': malicious_search})
        
        # Should return normal response, not cause error
        self.assertEqual(response.status_code, 200)
        
        # Alert should still exist (table not dropped)
        self.assertTrue(Alert.objects.filter(id=self.alert.id).exists())
    
    def test_xss_protection(self):
        """Test protection against XSS attacks"""
        # Create alert with potentially malicious content
        xss_content = "<script>alert('XSS')</script>"
        
        alert = Alert.objects.create(
            title=f"Alert {xss_content}",
            description=f"Description {xss_content}",
            category=self.category,
            severity="medium",
            latitude=Decimal('40.7590'),
            longitude=Decimal('-73.9850'),
            community=self.community,
            created_by=self.user,
            incident_datetime=timezone.now()
        )
        
        response = self.client.get(reverse('alert_detail', args=[alert.id]))
        
        # Script tags should be escaped in HTML
        self.assertNotContains(response, "<script>")
        self.assertContains(response, "&lt;script&gt;")
