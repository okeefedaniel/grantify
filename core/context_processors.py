"""Context processors for Harbor."""
from keel.core.context_processors import site_context as _keel_site_context


def site_context(request):
    """Extend Keel's site context with Harbor-specific variables."""
    ctx = _keel_site_context(request)
    if hasattr(request, 'user') and request.user.is_authenticated:
        from core.models import get_harbor_profile
        ctx['has_ai_access'] = get_harbor_profile(request.user).has_ai_access
    else:
        ctx['has_ai_access'] = False
    return ctx
