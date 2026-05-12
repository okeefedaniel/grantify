"""/api/v1/audit-feed/ — surfaces harbor's AuditLog to Keel's /audit/ page.

See keel/feed/audit_feed_example.py for the rollout pattern. Requires
keel >= 0.38.0 (provides audit_feed_view + fetch_product_audit).
"""
from __future__ import annotations

from datetime import datetime, timezone

from django.conf import settings
from django.db.models import Q
from django.utils import timezone as dj_tz

from keel.feed import audit_feed_view

from core.models import AuditLog


def _parse_iso(value, default):
    if not value:
        return default
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return default
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@audit_feed_view
def harbor_audit_feed(request):
    now = dj_tz.now()
    window_start = _parse_iso(request.GET.get('window_start'), now)
    window_end = _parse_iso(request.GET.get('window_end'), now)
    q = (request.GET.get('q') or '').strip()
    actions = [a for a in (request.GET.get('actions') or '').split(',') if a]
    try:
        limit = int(request.GET.get('limit') or 200)
    except (TypeError, ValueError):
        limit = 200
    limit = max(1, min(limit, 200))

    qs = AuditLog.objects.select_related('user').filter(
        timestamp__gte=window_start, timestamp__lte=window_end,
    ).order_by('-timestamp')
    if actions:
        qs = qs.filter(action__in=actions)
    if q:
        qs = qs.filter(
            Q(description__icontains=q)
            | Q(entity_type__icontains=q)
            | Q(entity_id__icontains=q)
            | Q(user__username__icontains=q)
            | Q(user__email__icontains=q),
        )

    total = qs.count()
    product_code = (getattr(settings, 'KEEL_PRODUCT_CODE', '') or
                    getattr(settings, 'KEEL_PRODUCT_NAME', '').lower())
    rows = []
    for entry in qs[:limit]:
        rows.append({
            'id': str(entry.id) if entry.id is not None else '',
            'timestamp': entry.timestamp.isoformat(),
            'action': entry.action,
            'action_display': entry.get_action_display(),
            'entity_type': entry.entity_type,
            'entity_id': entry.entity_id,
            'description': entry.description or '',
            'deep_link_snapshot': getattr(entry, 'deep_link_snapshot', '') or '',
            'ip_address': entry.ip_address,
            'user_username': entry.user.username if entry.user_id else '',
            'user_email': entry.user.email if entry.user_id else '',
            'product': product_code,
        })

    return {
        'items': rows,
        'total_in_window': total,
        'capped': total > limit,
        'window': [window_start.isoformat(), window_end.isoformat()],
        'fetched_at': dj_tz.now().isoformat(),
        'product': product_code,
    }
