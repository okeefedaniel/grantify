"""Personalize Harbor demo data for the cross-suite walkthrough persona.

The default ``seed_data.py`` assigns open ReviewAssignments to ``rev1``
(the demo reviewer persona) and never creates any ApplicationAssignment
rows at all. So when the cross-suite demo signs in as ``agency_admin``
(via demo-keel OIDC), Harbor's ``/api/v1/helm-feed/inbox/`` returns zero
items and the Helm dashboard's "Awaiting Me" column shows Harbor as empty.

This command:
  - reassigns 2-3 existing open (``assigned`` / ``in_progress``)
    ReviewAssignment rows to ``agency_admin`` so they surface as
    ball-in-this-user's-court items in Helm's per-user inbox,
  - claims 2-3 submitted/under-review Applications as
    ApplicationAssignment rows owned by ``agency_admin`` in the open
    (``assigned`` / ``in_progress``) state,
  - drops two unread Notification rows targeting ``agency_admin`` so
    Helm's Alerts column has Harbor content too.

Idempotent. Refuses to run unless ``DEMO_MODE=true`` (or ``--force``).
Run after ``seed_demo`` / ``seed_data.py`` so the underlying applications
and review assignments already exist.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


User = get_user_model()

PERSONA_USERNAME = 'agency_admin'

# Application project titles whose existing open ReviewAssignment row we
# reassign to agency_admin. These are seeded by seed_data.py with the
# reviewer pinned to rev1 (status 'assigned' or 'in_progress').
REVIEW_APP_TITLES = [
    'Healthcare Workforce Expansion Program',  # assigned, workforce rubric
    'Bridgeport Youth Trades Academy',          # in_progress, workforce rubric
    'AI-Powered Quality Inspection System',     # assigned, SBI rubric
]

# Submitted / under-review applications that agency_admin claims as the
# processing program officer (ApplicationAssignment). seed_data.py does
# NOT create ApplicationAssignment rows, so we create-or-update here.
ASSIGNMENT_APP_TITLES = [
    'Coastal Storm Surge Barrier System',
    'Downtown Capital Streetscape Phase I',
    'Frog Hollow Neighborhood Transformation',
]


class Command(BaseCommand):
    help = 'Personalize demo reviews / assignments / notifications for agency_admin.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force', action='store_true',
            help='Run even when DEMO_MODE is off (local dev only).',
        )

    def handle(self, *args, **opts):
        if not opts['force'] and not getattr(settings, 'DEMO_MODE', False):
            raise CommandError(
                'Refusing to seed without DEMO_MODE=true (use --force for local dev).'
            )

        try:
            persona = User.objects.get(username=PERSONA_USERNAME)
        except User.DoesNotExist:
            self.stdout.write(self.style.WARNING(
                f'Persona "{PERSONA_USERNAME}" not found — has seed_keel_users '
                'run? Skipping personalization.'
            ))
            return

        # Imports deferred so the command module can be imported even if
        # the apps aren't fully wired (e.g. during checks).
        from applications.models import Application, ApplicationAssignment
        from core.models import Notification
        from reviews.models import ReviewAssignment

        # ------------------------------------------------------------------
        # 1. Reassign existing open ReviewAssignment rows to agency_admin.
        # ------------------------------------------------------------------
        open_review_statuses = [
            ReviewAssignment.Status.ASSIGNED,
            ReviewAssignment.Status.IN_PROGRESS,
        ]
        review_reassigned = 0
        for title in REVIEW_APP_TITLES:
            ra = (
                ReviewAssignment.objects
                .filter(
                    application__project_title=title,
                    status__in=open_review_statuses,
                )
                .first()
            )
            if ra is None:
                self.stdout.write(self.style.WARNING(
                    f'  No open ReviewAssignment for "{title}" — skipping.'
                ))
                continue
            if ra.reviewer_id == persona.pk:
                self.stdout.write(
                    f'  ReviewAssignment already on {persona.username}: "{title}".'
                )
                continue
            ra.reviewer = persona
            ra.save(update_fields=['reviewer'])
            review_reassigned += 1
            self.stdout.write(
                f'  ReviewAssignment -> {persona.username}: "{title}" '
                f'({ra.get_status_display()}).'
            )

        # ------------------------------------------------------------------
        # 2. Create / refresh open ApplicationAssignment rows owned by
        #    agency_admin so "Process: <title>" items show in the inbox.
        # ------------------------------------------------------------------
        open_assignment_statuses = [
            ApplicationAssignment.Status.ASSIGNED,
            ApplicationAssignment.Status.IN_PROGRESS,
        ]
        assignment_claimed = 0
        for title in ASSIGNMENT_APP_TITLES:
            app = Application.objects.filter(project_title=title).first()
            if app is None:
                self.stdout.write(self.style.WARNING(
                    f'  No Application for "{title}" — skipping.'
                ))
                continue

            # If there's already an open assignment for this app, reassign
            # it to the persona rather than stacking duplicates.
            existing = (
                app.staff_assignments
                .filter(status__in=open_assignment_statuses)
                .first()
            )
            if existing is not None:
                if existing.assigned_to_id == persona.pk:
                    self.stdout.write(
                        f'  ApplicationAssignment already on {persona.username}: '
                        f'"{title}".'
                    )
                    continue
                existing.assigned_to = persona
                existing.assigned_by = persona
                existing.assignment_type = (
                    ApplicationAssignment.AssignmentType.CLAIMED
                )
                existing.save(update_fields=[
                    'assigned_to', 'assigned_by', 'assignment_type',
                ])
                assignment_claimed += 1
                self.stdout.write(
                    f'  ApplicationAssignment -> {persona.username}: "{title}" '
                    f'(reassigned existing open row).'
                )
                continue

            ApplicationAssignment.objects.create(
                application=app,
                assigned_to=persona,
                assigned_by=persona,
                assignment_type=ApplicationAssignment.AssignmentType.CLAIMED,
                status=ApplicationAssignment.Status.IN_PROGRESS,
            )
            assignment_claimed += 1
            self.stdout.write(
                f'  ApplicationAssignment -> {persona.username}: "{title}" '
                f'(new claim).'
            )

        # ------------------------------------------------------------------
        # 3. Two unread Notifications for the Helm Alerts column.
        #    Stable titles keep update_or_create idempotent.
        # ------------------------------------------------------------------
        notification_specs = [
            {
                'title': 'Review due: Healthcare Workforce Expansion Program',
                'message': (
                    'Scoring window closes in 3 business days. Workforce '
                    'rubric (5 criteria) — get your scores in to keep the '
                    'panel on schedule.'
                ),
                'priority': Notification.Priority.HIGH,
                'link': '/reviews/',
            },
            {
                'title': 'New claim: Coastal Storm Surge Barrier System',
                'message': (
                    'Town of Greenwich submitted a $1.8M Municipal '
                    'Infrastructure Resilience application. Compliance '
                    'verification pending your sign-off.'
                ),
                'priority': Notification.Priority.MEDIUM,
                'link': '/applications/',
            },
        ]
        for spec in notification_specs:
            Notification.objects.update_or_create(
                recipient=persona,
                title=spec['title'],
                defaults={
                    'message': spec['message'],
                    'priority': spec['priority'],
                    'link': spec['link'],
                    'is_read': False,
                },
            )
            self.stdout.write(f'  Notification: {spec["title"]}')

        self.stdout.write(self.style.SUCCESS(
            f'\nPersonalized Harbor inbox for {persona.username} '
            f'({review_reassigned} review(s) reassigned, '
            f'{assignment_claimed} assignment(s) claimed).'
        ))
