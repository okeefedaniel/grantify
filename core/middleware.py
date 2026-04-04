"""Harbor-specific middleware."""
from core.apps import _get_harbor_profile_cached


class HarborProfileMiddleware:
    """Attach HarborProfile fields (agency, organization) to the user instance.

    Must run AFTER AuthenticationMiddleware and ProductAccessMiddleware.
    This lets views use ``request.user.agency`` / ``request.user.organization``
    transparently, delegating to HarborProfile rather than KeelUser fields.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            profile = _get_harbor_profile_cached(user)
            # Shadow the KeelUser.agency FK with Harbor's agency on this instance
            user.__dict__['agency'] = profile.agency
            user.__dict__['agency_id'] = profile.agency_id
            user.__dict__['organization'] = profile.organization
            user.__dict__['organization_id'] = profile.organization_id
        return self.get_response(request)
