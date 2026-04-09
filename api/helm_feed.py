"""Harbor's /api/v1/helm-feed/ endpoint.

Exposes real-time metrics, action items, and alerts for Helm's
executive dashboard. This is the reference implementation — other
products should follow this pattern.
"""
from datetime import timedelta

from django.conf import settings
from django.db.models import Count, Q, Sum
from django.utils import timezone

from keel.feed.views import helm_feed_view


def _product_url():
    """Resolve the base product URL, respecting demo mode."""
    if getattr(settings, 'DEMO_MODE', False):
        return 'https://demo-harbor.docklabs.ai'
    return 'https://harbor.docklabs.ai'


@helm_feed_view
def harbor_helm_feed(request):
    """Build Harbor's feed payload from live data."""
    from applications.models import Application
    from awards.models import Award
    from financial.models import DrawdownRequest
    from grants.models import GrantProgram
    from reporting.models import Report

    now = timezone.now()
    base_url = _product_url()

    # ── Metrics ──────────────────────────────────────────────────
    active_grants = GrantProgram.objects.filter(
        status__in=['posted', 'accepting_applications', 'under_review', 'awards_pending'],
    ).count()

    active_awards = Award.objects.filter(
        status__in=['active', 'executed'],
    )
    active_award_count = active_awards.count()
    ytd_disbursed = int(
        DrawdownRequest.objects.filter(
            status='paid',
            paid_at__year=now.year,
        ).aggregate(total=Sum('amount'))['total'] or 0
    )

    pipeline_count = Application.objects.filter(
        status__in=['submitted', 'under_review'],
    ).count()

    total_award_value = int(
        active_awards.aggregate(total=Sum('award_amount'))['total'] or 0
    )

    metrics = [
        {
            'key': 'active_grants',
            'label': 'Active Programs',
            'value': active_grants,
            'unit': None,
            'trend': None,
            'trend_value': None,
            'trend_period': None,
            'severity': 'normal',
            'deep_link': f'{base_url}/grants/?status=active',
        },
        {
            'key': 'ytd_disbursed',
            'label': 'YTD Disbursed',
            'value': ytd_disbursed,
            'unit': 'USD',
            'trend': None,
            'trend_value': None,
            'trend_period': None,
            'severity': 'normal',
            'deep_link': f'{base_url}/financial/',
        },
        {
            'key': 'pipeline_count',
            'label': 'In Pipeline',
            'value': pipeline_count,
            'unit': None,
            'trend': None,
            'trend_value': None,
            'trend_period': None,
            'severity': 'normal',
            'deep_link': f'{base_url}/applications/',
        },
        {
            'key': 'active_awards',
            'label': 'Active Awards',
            'value': active_award_count,
            'unit': None,
            'trend': None,
            'trend_value': None,
            'trend_period': None,
            'severity': 'normal',
            'deep_link': f'{base_url}/awards/?status=active',
        },
        {
            'key': 'total_award_value',
            'label': 'Total Award Value',
            'value': total_award_value,
            'unit': 'USD',
            'trend': None,
            'trend_value': None,
            'trend_period': None,
            'severity': 'normal',
            'deep_link': f'{base_url}/awards/',
        },
    ]

    # ── Action Items ─────────────────────────────────────────────
    action_items = []

    # Pending application reviews
    pending_apps = (
        Application.objects
        .filter(status__in=['submitted', 'under_review'])
        .select_related('grant_program', 'organization')
        .order_by('submitted_at')[:10]
    )
    for app in pending_apps:
        action_items.append({
            'id': f'harbor-app-review-{app.pk}',
            'type': 'review',
            'title': f'Review: {app.grant_program.title} — {app.organization.name}',
            'description': f'Application {app.get_status_display().lower()}',
            'priority': 'high' if app.status == 'submitted' else 'medium',
            'due_date': '',
            'assigned_to_role': 'program_officer',
            'deep_link': f'{base_url}/applications/{app.pk}/',
            'created_at': app.submitted_at.isoformat() if app.submitted_at else '',
        })

    # Pending drawdown approvals
    pending_drawdowns = (
        DrawdownRequest.objects
        .filter(status__in=['submitted', 'under_review'])
        .select_related('award', 'award__grant_program')
        .order_by('submitted_at')[:5]
    )
    for dr in pending_drawdowns:
        action_items.append({
            'id': f'harbor-drawdown-{dr.pk}',
            'type': 'approval',
            'title': f'Approve drawdown: ${dr.amount:,.0f} — {dr.award.grant_program.title}',
            'description': f'Drawdown request {dr.get_status_display().lower()}',
            'priority': 'medium',
            'due_date': '',
            'assigned_to_role': 'fiscal_officer',
            'deep_link': f'{base_url}/financial/drawdowns/{dr.pk}/',
            'created_at': dr.submitted_at.isoformat() if dr.submitted_at else '',
        })

    # Pending award approvals
    pending_awards = (
        Award.objects
        .filter(status='pending_approval')
        .select_related('grant_program', 'organization')
        .order_by('-created_at')[:5]
    )
    for award in pending_awards:
        action_items.append({
            'id': f'harbor-award-approve-{award.pk}',
            'type': 'approval',
            'title': f'Approve award: ${award.award_amount:,.0f} — {award.organization.name}',
            'description': f'{award.grant_program.title}',
            'priority': 'high',
            'due_date': '',
            'assigned_to_role': 'program_director',
            'deep_link': f'{base_url}/awards/{award.pk}/',
            'created_at': award.created_at.isoformat() if award.created_at else '',
        })

    # ── Alerts ───────────────────────────────────────────────────
    alerts = []

    # Overdue reports
    overdue_reports = Report.objects.filter(
        status__in=['draft', 'submitted'],
        due_date__lt=now.date(),
    ).count()
    if overdue_reports > 0:
        alerts.append({
            'id': 'harbor-overdue-reports',
            'type': 'overdue',
            'title': f'{overdue_reports} overdue report{"s" if overdue_reports != 1 else ""}',
            'severity': 'warning' if overdue_reports <= 3 else 'critical',
            'since': '',
            'deep_link': f'{base_url}/reporting/?status=overdue',
        })

    # Awards expiring within 30 days
    expiring_soon = Award.objects.filter(
        status__in=['active', 'executed'],
        end_date__lte=now.date() + timedelta(days=30),
        end_date__gte=now.date(),
    ).count()
    if expiring_soon > 0:
        alerts.append({
            'id': 'harbor-expiring-awards',
            'type': 'deadline',
            'title': f'{expiring_soon} award{"s" if expiring_soon != 1 else ""} expiring within 30 days',
            'severity': 'warning',
            'since': '',
            'deep_link': f'{base_url}/awards/?expiring=30',
        })

    # ── Sparklines ───────────────────────────────────────────────
    # Monthly application volume for last 12 months
    sparkline_values = []
    sparkline_labels = []
    for i in range(11, -1, -1):
        month_start = (now - timedelta(days=i * 30)).replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1)
        count = Application.objects.filter(
            submitted_at__gte=month_start,
            submitted_at__lt=month_end,
        ).count()
        sparkline_values.append(count)
        sparkline_labels.append(month_start.strftime('%b'))

    sparklines = {}
    if any(v > 0 for v in sparkline_values):
        sparklines['pipeline_count'] = {
            'values': sparkline_values,
            'labels': sparkline_labels,
            'period': 'month',
        }

    return {
        'product': 'harbor',
        'product_label': 'Harbor',
        'product_url': f'{base_url}/dashboard/',
        'metrics': metrics,
        'action_items': action_items,
        'alerts': alerts,
        'sparklines': sparklines,
    }
