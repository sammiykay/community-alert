from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import CustomUser, Alert, AlertCategory, Community


class UserRegistrationForm(UserCreationForm):
    """User registration form with additional fields"""
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=20, required=False)
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'phone_number', 'password1', 'password2')
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError('A user with this email already exists.')
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.phone_number = self.cleaned_data.get('phone_number', '')
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    """Form for updating basic user profile information"""
    
    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'phone_number', 'communities'
        ]
        widgets = {
            'communities': forms.CheckboxSelectMultiple(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add CSS classes to form fields
        for field_name, field in self.fields.items():
            if field_name != 'communities':
                field.widget.attrs['class'] = 'form-control'
        # Filter active communities
        self.fields['communities'].queryset = Community.objects.filter(is_active=True)


class CommunityForm(forms.ModelForm):
    """Form for creating communities (admin-only)"""
    
    class Meta:
        model = Community
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Community name (e.g., Akungba Akoko)'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional description of the community'}),
        }


class UserNotificationForm(forms.ModelForm):
    """Form for updating user notification preferences"""
    
    class Meta:
        model = CustomUser
        fields = [
            'email_notifications', 'push_notifications'
        ]
        widgets = {
            'email_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'push_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class AlertForm(forms.ModelForm):
    """Form for creating and editing alerts"""
    
    class Meta:
        model = Alert
        fields = [
            'title', 'description', 'category', 'severity', 'status',
            'address', 'community', 'incident_datetime', 'is_public'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Brief title for the alert'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Detailed description of the incident'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'severity': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street address or landmark (optional)'}),
            'community': forms.Select(attrs={'class': 'form-control'}),
            'incident_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Filter active categories and communities
        self.fields['category'].queryset = AlertCategory.objects.filter(is_active=True)
        self.fields['community'].queryset = Community.objects.filter(is_active=True)
        
        # If user is provided, filter communities to only those the user belongs to
        if user and not user.is_staff:
            self.fields['community'].queryset = user.communities.filter(is_active=True)
        
        # Set default incident datetime to now
        if not self.instance.pk:
            from django.utils import timezone
            self.fields['incident_datetime'].initial = timezone.now()


class AlertCommentForm(forms.Form):
    """Form for adding comments to alerts"""
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Add your comment...'
        }),
        max_length=1000,
        required=True
    )


class AlertMediaForm(forms.Form):
    """Form for uploading media to alerts"""
    media_file = forms.FileField(
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*,video/*'
        }),
        required=True
    )
    caption = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Optional caption for the media'
        }),
        max_length=300,
        required=False
    )
    
    def clean_media_file(self):
        file = self.cleaned_data.get('media_file')
        if file:
            # Check file size (50MB limit)
            if file.size > 50 * 1024 * 1024:
                raise ValidationError('File size cannot exceed 50MB.')
            
            # Check file type
            allowed_types = [
                'image/jpeg', 'image/png', 'image/gif',
                'video/mp4', 'video/webm', 'video/quicktime'
            ]
            if file.content_type not in allowed_types:
                raise ValidationError('File type not supported. Please upload images (JPEG, PNG, GIF) or videos (MP4, WebM).')
        
        return file


class AlertSearchForm(forms.Form):
    """Form for searching and filtering alerts"""
    search = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search alerts...'
        }),
        required=False
    )
    category = forms.ModelChoiceField(
        queryset=AlertCategory.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False,
        empty_label='All Categories'
    )
    severity = forms.ChoiceField(
        choices=[('', 'All Severities')] + Alert.SEVERITY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + Alert.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )
    community = forms.ModelChoiceField(
        queryset=Community.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False,
        empty_label='All Communities'
    )


# ============================================================================
# ADMIN FORMS
# ============================================================================

class AlertCategoryForm(forms.ModelForm):
    """Form for creating and editing alert categories (admin-only)"""
    
    class Meta:
        model = AlertCategory
        fields = ['name', 'description', 'icon', 'color', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Category name (e.g., "Break-in & Burglary")'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Brief description of this category'
            }),
            'icon': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Font Awesome icon class (e.g., "fas fa-user-secret")'
            }),
            'color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'value': '#007bff'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class AdminUserForm(forms.ModelForm):
    """Form for editing users (admin-only)"""
    
    class Meta:
        model = CustomUser
        fields = [
            'username', 'email', 'first_name', 'last_name', 
            'role', 'is_active', 'email_notifications', 'push_notifications',
            'communities'
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'push_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'communities': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        }


# ============================================================================
# SUPERUSER FORMS
# ============================================================================

class CreateAdminUserForm(forms.ModelForm):
    """Form for creating new administrator users (superuser-only)"""
    
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='Password must be at least 8 characters long.'
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='Enter the same password as before, for verification.'
    )
    
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Unique username for the administrator'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Administrator email address'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name'
            }),
        }
    
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords don't match")
        return password2
    
    def clean_password1(self):
        password1 = self.cleaned_data.get("password1")
        if password1 and len(password1) < 8:
            raise ValidationError("Password must be at least 8 characters long")
        return password1
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.role = 'admin'
        user.is_staff = True
        user.email_notifications = True
        user.push_notifications = True
        if commit:
            user.save()
        return user