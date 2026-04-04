"""Test helpers for Harbor — creates KeelUser with ProductAccess + HarborProfile."""
from django.contrib.auth import get_user_model
from keel.accounts.models import ProductAccess
from core.models import HarborProfile, get_harbor_profile

User = get_user_model()


def create_test_user(username='testuser', email=None, role='applicant',
                     agency=None, organization=None, **kwargs):
    """Create a KeelUser with ProductAccess and HarborProfile for testing."""
    if email is None:
        email = f'{username}@example.com'
    user = User.objects.create_user(username, email, **kwargs)
    ProductAccess.objects.create(user=user, product='harbor', role=role, is_active=True)
    profile = get_harbor_profile(user)
    if agency:
        profile.agency = agency
    if organization:
        profile.organization = organization
    profile.save()
    # Set role on user instance so middleware-less test code works
    user._product_role = role
    return user
