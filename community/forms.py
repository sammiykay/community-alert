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
    """Form for updating user profile"""
    
    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'email', 'phone_number', 
            'latitude', 'longitude', 'notification_radius_km',
            'email_notifications', 'push_notifications'
        ]
        widgets = {
            'latitude': forms.NumberInput(attrs={'step': 'any', 'class': 'form-control'}),
            'longitude': forms.NumberInput(attrs={'step': 'any', 'class': 'form-control'}),
            'notification_radius_km': forms.NumberInput(attrs={'min': '0.1', 'max': '50', 'step': '0.1', 'class': 'form-control'}),
            'email_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'push_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add CSS classes to form fields
        for field_name, field in self.fields.items():
            if field_name not in ['email_notifications', 'push_notifications']:
                field.widget.attrs['class'] = 'form-control'


class AlertForm(forms.ModelForm):
    """Form for creating and editing alerts"""
    
    class Meta:
        model = Alert
        fields = [
            'title', 'description', 'category', 'severity', 'status',
            'latitude', 'longitude', 'address', 'community',
            'incident_datetime', 'is_public'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Brief title for the alert'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Detailed description of the incident'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'severity': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={'step': 'any', 'class': 'form-control', 'placeholder': 'Click on map to set location'}),
            'longitude': forms.NumberInput(attrs={'step': 'any', 'class': 'form-control', 'placeholder': 'Click on map to set location'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street address or landmark'}),
            'community': forms.Select(attrs={'class': 'form-control'}),
            'incident_datetime': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter active categories and communities
        self.fields['category'].queryset = AlertCategory.objects.filter(is_active=True)
        self.fields['community'].queryset = Community.objects.filter(is_active=True)
        
        # Set default incident datetime to now
        if not self.instance.pk:
            from django.utils import timezone
            self.fields['incident_datetime'].initial = timezone.now()
    
    def clean(self):
        cleaned_data = super().clean()
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')
        
        if not latitude or not longitude:
            raise ValidationError('Please set the location by clicking on the map or entering coordinates.')
        
        return cleaned_data


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