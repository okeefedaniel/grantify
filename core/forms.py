from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext_lazy as _lazy

from .models import Agency, Organization, OrganizationClaim, OrganizationContact
from keel.accounts.forms import LoginForm  # noqa: F401  (shared across DockLabs suite)

User = get_user_model()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
class RegistrationForm(UserCreationForm):
    """Public registration form for new applicant users."""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _lazy('Email address'),
        }),
    )
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _lazy('First name'),
        }),
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _lazy('Last name'),
        }),
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _lazy('Phone number (optional)'),
        }),
    )
    organization = forms.ModelChoiceField(
        queryset=Organization.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text=_lazy('Select your organization, if applicable.'),
    )
    accepted_terms = forms.BooleanField(
        required=True,
        label=_lazy('I accept the Terms of Service and Privacy Policy'),
    )

    class Meta:
        model = User
        fields = (
            'username', 'email', 'first_name', 'last_name',
            'phone',
            'password1', 'password2', 'accepted_terms',
        )
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _lazy('Username'),
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': _lazy('Password'),
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': _lazy('Confirm password'),
        })

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.phone = self.cleaned_data.get('phone', '')
        user.is_state_user = False
        if self.cleaned_data.get('accepted_terms'):
            user.accepted_terms = True
            from django.utils import timezone
            user.accepted_terms_at = timezone.now()
        if commit:
            user.save()
            # Link organization via HarborProfile
            org = self.cleaned_data.get('organization')
            if org:
                from .models import get_harbor_profile
                profile = get_harbor_profile(user)
                profile.organization = org
                profile.save(update_fields=['organization'])
            # Set default applicant role via ProductAccess
            from keel.accounts.models import ProductAccess
            ProductAccess.objects.get_or_create(
                user=user, product='harbor',
                defaults={'role': 'applicant', 'is_active': True},
            )
        return user


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
# LoginForm is now shared in Keel for suite-wide consistency.
# See keel/accounts/forms.py for the canonical definition.

# ---------------------------------------------------------------------------
# Organization
# ---------------------------------------------------------------------------
class OrganizationForm(forms.ModelForm):
    """Form for creating or updating an Organization."""

    class Meta:
        model = Organization
        fields = (
            'name', 'org_type',
            'duns_number', 'uei_number', 'ein',
            'sam_registered', 'sam_expiration',
            'address_line1', 'address_line2', 'city', 'state', 'zip_code',
            'phone', 'website',
            'notes',
        )
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'org_type': forms.Select(attrs={'class': 'form-select'}),
            'duns_number': forms.TextInput(attrs={'class': 'form-control'}),
            'uei_number': forms.TextInput(attrs={'class': 'form-control'}),
            'ein': forms.TextInput(attrs={'class': 'form-control'}),
            'sam_expiration': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date',
            }),
            'address_line1': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line2': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '2'}),
            'zip_code': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
class ProfileForm(forms.ModelForm):
    """Form for editing the authenticated user's profile."""

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'title', 'phone')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }


# ---------------------------------------------------------------------------
# User Role Management (System Admin only)
# ---------------------------------------------------------------------------
class UserRoleForm(forms.Form):
    """Form for system admins to update a user's role, agency, and flags.

    Role is stored in ProductAccess; agency in HarborProfile; flags on KeelUser.
    """

    ROLE_CHOICES = [
        ('system_admin', 'System Administrator'),
        ('agency_admin', 'Agency Administrator'),
        ('program_officer', 'Program Officer'),
        ('fiscal_officer', 'Fiscal Officer'),
        ('federal_coordinator', 'Federal Fund Coordinator'),
        ('reviewer', 'Reviewer'),
        ('applicant', 'Applicant'),
        ('auditor', 'Auditor'),
    ]

    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    agency = forms.ModelChoiceField(
        queryset=Agency.objects.filter(is_active=True).order_by('name'),
        required=False, widget=forms.Select(attrs={'class': 'form-select'}),
    )
    is_state_user = forms.BooleanField(required=False, label=_lazy('State Employee'))
    is_active = forms.BooleanField(required=False, label=_lazy('Account Active'))

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user
        if user:
            from keel.accounts.models import ProductAccess
            from .models import get_harbor_profile
            access = ProductAccess.objects.filter(user=user, product='harbor').first()
            profile = get_harbor_profile(user)
            self.initial['role'] = access.role if access else 'applicant'
            self.initial['agency'] = profile.agency_id
            self.initial['is_state_user'] = user.is_state_user
            self.initial['is_active'] = user.is_active

    def save(self):
        user = self._user
        from keel.accounts.models import ProductAccess
        from .models import get_harbor_profile

        ProductAccess.objects.update_or_create(
            user=user, product='harbor',
            defaults={'role': self.cleaned_data['role'], 'is_active': True},
        )
        profile = get_harbor_profile(user)
        profile.agency = self.cleaned_data.get('agency')
        profile.save(update_fields=['agency'])
        user.is_state_user = self.cleaned_data['is_state_user']
        user.is_active = self.cleaned_data['is_active']
        user.save(update_fields=['is_state_user', 'is_active'])
        return user


# ---------------------------------------------------------------------------
# Organization Claim Review
# ---------------------------------------------------------------------------
class ClaimReviewForm(forms.Form):
    """Form for Program Officers to approve or deny an organization claim."""

    action = forms.ChoiceField(
        choices=[('approve', _lazy('Approve')), ('deny', _lazy('Deny'))],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
    )
    reviewer_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _lazy('Optional notes about this decision...'),
        }),
    )


# ---------------------------------------------------------------------------
# Organization Contact Assignment
# ---------------------------------------------------------------------------
class OrganizationContactForm(forms.ModelForm):
    """Form for assigning a staff contact to an organization."""

    class Meta:
        model = OrganizationContact
        fields = ('assigned_to', 'notes')
        widgets = {
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'assigned_to': _lazy('Assign To'),
            'notes': _lazy('Notes'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from keel.accounts.models import ProductAccess
        staff_ids = ProductAccess.objects.filter(
            product='harbor',
            role__in=['program_officer', 'agency_admin', 'system_admin'],
            is_active=True,
        ).values_list('user_id', flat=True)
        self.fields['assigned_to'].queryset = User.objects.filter(
            pk__in=staff_ids,
            is_active=True,
        ).order_by('last_name', 'first_name')
