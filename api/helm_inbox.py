"""Harbor's /api/v1/helm-feed/inbox/ endpoint — per-user inbox.

Items where the requesting user is the gating dependency right now in
Harbor: open application reviews assigned to them, open application
staff assignments claimed by them. Drawdown approvals are role-based
(no per-user FK on DrawdownRequest); we leave them to the aggregate
endpoint until that model gets an explicit approver field.

Conforms to the UserInbox shape in helm.dashboard.feed_contract.
Auth + cache + sub-resolution come from keel.feed.helm_inbox_view.
"""
from django.conf import settings
from keel.feed.views import helm_inbox_view

from .helm_feed import _product_url


@helm_inbox_view
def harbor_helm_feed_inbox(request, user):
    from applications.models import ApplicationAssignment
    from core.models import Notification
    from reviews.models import ReviewAssignment

    base_url = _product_url().rstrip('/')
    items = []

    # Open review assignments — user is the assigned reviewer.
    open_review_statuses = [
        ReviewAssignment.Status.ASSIGNED,
        ReviewAssignment.Status.IN_PROGRESS,
    ]
    review_qs = (
        ReviewAssignment.objects
        .filter(reviewer=user, status__in=open_review_statuses)
        .select_related('application', 'application__organization')
        .order_by('assigned_at')
    )
    for ra in review_qs:
        app = ra.application
        org_name = getattr(getattr(app, 'organization', None), 'name', '') or ''
        title_label = getattr(app, 'project_title', None) or org_name or f'Application {app.pk}'
        items.append({
            'id': str(ra.id),
            'type': 'review',
            'title': f'Review: {title_label}',
            'deep_link': f'{base_url}/applications/{app.pk}/',
            'waiting_since': ra.assigned_at.isoformat() if getattr(ra, 'assigned_at', None) else '',
            'due_date': None,
            'priority': 'high',
        })

    # Open processing assignments — user is the assigned program officer.
    open_assignment_statuses = [
        ApplicationAssignment.Status.ASSIGNED,
        ApplicationAssignment.Status.IN_PROGRESS,
    ]
    assignment_qs = (
        ApplicationAssignment.objects
        .filter(assigned_to=user, status__in=open_assignment_statuses)
        .select_related('application', 'application__organization')
        .order_by('-claimed_at')
    )
    for aa in assignment_qs:
        app = aa.application
        org_name = getattr(getattr(app, 'organization', None), 'name', '') or ''
        title_label = getattr(app, 'project_title', None) or org_name or f'Application {app.pk}'
        items.append({
            'id': str(aa.id),
            'type': 'assignment',
            'title': f'Process: {title_label}',
            'deep_link': f'{base_url}/applications/{app.pk}/',
            'waiting_since': aa.claimed_at.isoformat() if getattr(aa, 'claimed_at', None) else '',
            'due_date': None,
            'priority': 'normal',
        })

    unread = (
        Notification.objects
        .filter(recipient=user, is_read=False)
        .order_by('-created_at')[:50]
    )
    notifications = []
    for n in unread:
        link = n.link or ''
        if link and base_url and link.startswith('/'):
            link = f'{base_url}{link}'
        notifications.append({
            'id': str(n.id),
            'title': n.title,
            'body': getattr(n, 'message', '') or '',
            'deep_link': link,
            'created_at': n.created_at.isoformat(),
            'priority': (n.priority or 'normal').lower(),
        })

    return {
        'product': getattr(settings, 'KEEL_PRODUCT_CODE', 'harbor'),
        'product_label': getattr(settings, 'KEEL_PRODUCT_NAME', 'Harbor'),
        'product_url': base_url,
        'user_sub': '',  # filled by decorator
        'items': items,
        'unread_notifications': notifications,
        'fetched_at': '',  # filled by decorator
    }
