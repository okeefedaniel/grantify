from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SignaturesConfig(AppConfig):
    name = 'signatures'
    default_auto_field = 'django.db.models.BigAutoField'
    verbose_name = _('Signatures')

    def ready(self):
        self._register_notification_types()

    def _register_notification_types(self):
        try:
            from keel.notifications import register, NotificationType
        except ImportError:
            return

        register(NotificationType(
            key='signature_required',
            label='Signature Required',
            description='You are the next signer in a document signing flow.',
            category='Signatures',
            default_channels=['in_app', 'email'],
            priority='high',
            email_template='emails/signer_active.html',
            email_subject='Action Required: Signature Needed — {title}',
            allow_mute=False,
        ))

        register(NotificationType(
            key='signing_complete',
            label='Signing Complete',
            description='All signatures have been collected for a document.',
            category='Signatures',
            default_channels=['in_app', 'email'],
            priority='high',
            email_template='emails/packet_completed.html',
            email_subject='Signing Complete — {title}',
        ))

        register(NotificationType(
            key='signing_declined',
            label='Signature Declined',
            description='A signer has declined to sign a document.',
            category='Signatures',
            default_channels=['in_app', 'email'],
            priority='high',
            email_template='emails/packet_declined.html',
            email_subject='Signature Declined — {title}',
        ))

        register(NotificationType(
            key='signature_reminder',
            label='Signature Reminder',
            description='A reminder that your signature is needed.',
            category='Signatures',
            default_channels=['in_app', 'email'],
            priority='high',
            email_template='emails/signer_reminder.html',
            email_subject='Reminder: Signature Needed — {title}',
        ))
