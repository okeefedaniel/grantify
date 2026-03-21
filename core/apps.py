from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        from allauth.account.signals import user_signed_up
        from keel.notifications import NotificationType, register

        def on_user_signed_up(sender, request, user, **kwargs):
            from core.notifications import notify_new_user_registered
            notify_new_user_registered(user)

        user_signed_up.connect(on_user_signed_up)

        # -- Register Harbor notification types --
        register(NotificationType(
            key='application_submitted',
            label='Application Submitted',
            description='A new grant application has been submitted for review.',
            category='Applications',
            default_channels=['in_app', 'email'],
            default_roles=['system_admin', 'agency_admin', 'program_officer'],
            priority='medium',
        ))
        register(NotificationType(
            key='application_status_changed',
            label='Application Status Changed',
            description='An application status has been updated (approved, denied, revision requested, etc.).',
            category='Applications',
            default_channels=['in_app', 'email'],
            default_roles=['applicant'],
            priority='high',
        ))
        register(NotificationType(
            key='award_created',
            label='Award Created',
            description='A new award has been created for an approved application.',
            category='Awards',
            default_channels=['in_app', 'email'],
            default_roles=['applicant'],
            priority='high',
        ))
        register(NotificationType(
            key='drawdown_status_changed',
            label='Drawdown Status Changed',
            description='A cash drawdown request status has been updated.',
            category='Financial',
            default_channels=['in_app', 'email'],
            default_roles=['applicant'],
            priority='high',
        ))
        register(NotificationType(
            key='report_reviewed',
            label='Report Reviewed',
            description='A submitted report has been reviewed (approved, revision requested, or rejected).',
            category='Reporting',
            default_channels=['in_app', 'email'],
            default_roles=['applicant'],
            priority='high',
        ))
        register(NotificationType(
            key='amendment_requested',
            label='Amendment Requested',
            description='A new award amendment has been requested.',
            category='Awards',
            default_channels=['in_app', 'email'],
            default_roles=['system_admin', 'agency_admin', 'program_officer'],
            priority='medium',
        ))
        register(NotificationType(
            key='signature_requested',
            label='Signature Requested',
            description='An award agreement has been sent for electronic signature.',
            category='Awards',
            default_channels=['in_app', 'email'],
            default_roles=['applicant'],
            priority='high',
        ))
        register(NotificationType(
            key='signature_completed',
            label='Signature Completed',
            description='An award agreement has been signed.',
            category='Awards',
            default_channels=['in_app', 'email'],
            default_roles=['system_admin', 'agency_admin', 'program_officer'],
            priority='high',
        ))
        register(NotificationType(
            key='closeout_initiated',
            label='Closeout Initiated',
            description='The closeout process has been initiated for an award.',
            category='Closeout',
            default_channels=['in_app', 'email'],
            default_roles=['applicant'],
            priority='high',
        ))
        register(NotificationType(
            key='organization_claim_submitted',
            label='Organization Claim Submitted',
            description='A user has claimed an organization and needs staff review.',
            category='Organizations',
            default_channels=['in_app'],
            default_roles=['system_admin', 'agency_admin', 'program_officer'],
            priority='medium',
        ))
        register(NotificationType(
            key='organization_claim_reviewed',
            label='Organization Claim Reviewed',
            description='An organization claim has been approved or denied.',
            category='Organizations',
            default_channels=['in_app'],
            default_roles=['applicant'],
            priority='high',
        ))
        register(NotificationType(
            key='new_user_registered',
            label='New User Registration',
            description='A new user has registered on the platform.',
            category='Users',
            default_channels=['in_app'],
            default_roles=['system_admin'],
            priority='medium',
        ))
        register(NotificationType(
            key='grant_match_found',
            label='AI Grant Match Found',
            description='The AI matching engine found a relevant grant opportunity.',
            category='Matching',
            default_channels=['in_app', 'email'],
            default_roles=['applicant', 'federal_coordinator'],
            priority='medium',
        ))
