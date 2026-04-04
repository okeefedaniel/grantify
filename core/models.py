import base64
import hashlib
import logging
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from keel.core.models import AbstractAuditLog, AbstractNotification
from keel.notifications.models import AbstractNotificationPreference, AbstractNotificationLog

logger = logging.getLogger(__name__)

# Role constants — used by mixins, views, and the WorkflowEngine.
# The actual role value comes from ProductAccess via middleware (user.role).
AGENCY_STAFF_ROLES = {
    'system_admin', 'agency_admin', 'program_officer',
    'fiscal_officer', 'federal_coordinator',
}
GRANT_MANAGER_ROLES = {
    'system_admin', 'agency_admin', 'program_officer', 'federal_coordinator',
}
FEDERAL_MANAGER_ROLES = {'system_admin', 'federal_coordinator'}
REVIEWER_ROLES = {'system_admin', 'agency_admin', 'program_officer', 'reviewer'}


def is_agency_staff(user):
    return getattr(user, 'role', '') in AGENCY_STAFF_ROLES


def can_manage_grants(user):
    return getattr(user, 'role', '') in GRANT_MANAGER_ROLES


def can_manage_federal(user):
    return getattr(user, 'role', '') in FEDERAL_MANAGER_ROLES


def can_review(user):
    return getattr(user, 'role', '') in REVIEWER_ROLES


def users_with_roles(*roles):
    """Return a User queryset filtered to users with the given Harbor roles.

    Roles are stored in ProductAccess, not on KeelUser, so this joins through
    that table.  Example: ``users_with_roles('system_admin', 'program_officer')``
    """
    from django.contrib.auth import get_user_model
    from keel.accounts.models import ProductAccess
    ids = ProductAccess.objects.filter(
        product='harbor', role__in=roles, is_active=True,
    ).values_list('user_id', flat=True)
    return get_user_model().objects.filter(pk__in=ids, is_active=True)


# ---------------------------------------------------------------------------
# Organization
# ---------------------------------------------------------------------------
class Organization(models.Model):
    """External entity that applies for or receives grants."""

    class OrgType(models.TextChoices):
        MUNICIPALITY = 'municipality', _('Municipality')
        NONPROFIT = 'nonprofit', _('Nonprofit')
        BUSINESS = 'business', _('Business')
        INDIVIDUAL = 'individual', _('Individual')
        TRIBAL = 'tribal', _('Tribal Nation')
        EDUCATIONAL = 'educational', _('Educational Institution')
        OTHER = 'other', _('Other')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    org_type = models.CharField(
        max_length=20,
        choices=OrgType.choices,
        default=OrgType.NONPROFIT,
        verbose_name=_('Organization Type'),
    )

    # Federal identifiers
    duns_number = models.CharField(
        max_length=13, blank=True, verbose_name=_('DUNS Number'),
    )
    uei_number = models.CharField(
        max_length=12, blank=True, verbose_name=_('UEI Number'),
    )
    ein = models.CharField(
        max_length=10, blank=True, verbose_name=_('EIN'),
    )

    # SAM registration
    sam_registered = models.BooleanField(
        default=False, verbose_name=_('SAM Registered'),
    )
    sam_expiration = models.DateField(
        null=True, blank=True, verbose_name=_('SAM Expiration Date'),
    )

    # Address
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=2, default='CT')
    zip_code = models.CharField(max_length=10, blank=True)

    # Contact
    phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)

    is_active = models.BooleanField(default=True)
    is_high_priority = models.BooleanField(
        default=False,
        verbose_name=_('High Priority'),
        help_text=_('Manually flagged as high-priority for assigned contact tracking.'),
    )
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = _('Organization')
        verbose_name_plural = _('Organizations')

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Agency  (state agencies)
# ---------------------------------------------------------------------------
class Agency(models.Model):
    """State agency that administers grants."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    abbreviation = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)

    # State ERP financial codes
    department_code = models.CharField(
        max_length=8, blank=True, verbose_name=_('State ERP Department Code'),
    )
    fund_code = models.CharField(
        max_length=5, blank=True, verbose_name=_('Fund Code'),
    )
    program_code = models.CharField(
        max_length=5, blank=True, verbose_name=_('Program Code'),
    )

    # Primary contact
    contact_name = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)

    address = models.TextField(blank=True)
    website = models.URLField(blank=True)

    can_be_grantee = models.BooleanField(
        default=False,
        help_text=_('Can this agency receive grants from other agencies?'),
    )
    can_be_grantor = models.BooleanField(
        default=True,
        help_text=_('Can this agency award grants?'),
    )

    is_active = models.BooleanField(default=True)
    onboarded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['abbreviation']
        verbose_name = _('Agency')
        verbose_name_plural = _('Agencies')

    def __str__(self):
        return f"{self.abbreviation} - {self.name}"


# ---------------------------------------------------------------------------
# HarborProfile — product-specific fields on KeelUser
# ---------------------------------------------------------------------------
class HarborProfile(models.Model):
    """Product-specific fields for Harbor users.

    KeelUser handles identity (email, name, title, phone, is_state_user,
    accepted_terms). HarborProfile stores Harbor-specific data.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='harbor_profile',
    )
    agency = models.ForeignKey(
        Agency, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='harbor_users',
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='harbor_users',
    )
    anthropic_api_key = models.CharField(
        max_length=255, blank=True, default='',
        verbose_name=_('Anthropic API Key'),
    )

    class Meta:
        verbose_name = _('Harbor Profile')
        verbose_name_plural = _('Harbor Profiles')

    def __str__(self):
        return f"Profile: {self.user}"

    @staticmethod
    def _get_fernet():
        from cryptography.fernet import Fernet
        key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        return Fernet(base64.urlsafe_b64encode(key))

    def set_anthropic_api_key(self, raw_key):
        if not raw_key:
            self.anthropic_api_key = ''
            return
        encrypted = self._get_fernet().encrypt(raw_key.encode()).decode()
        self.anthropic_api_key = encrypted

    def get_anthropic_api_key(self):
        if not self.anthropic_api_key:
            return ''
        try:
            return self._get_fernet().decrypt(
                self.anthropic_api_key.encode()
            ).decode()
        except Exception:
            logger.warning('Failed to decrypt API key for user %s', self.user_id)
            return ''

    @property
    def has_ai_access(self):
        return bool(self.anthropic_api_key) or bool(getattr(settings, 'ANTHROPIC_API_KEY', ''))


def get_harbor_profile(user):
    """Get or create HarborProfile for a user."""
    profile, _ = HarborProfile.objects.get_or_create(user=user)
    return profile


# ---------------------------------------------------------------------------
# AuditLog
# ---------------------------------------------------------------------------
class AuditLog(AbstractAuditLog):
    """Harbor audit log — inherits from Keel's immutable AbstractAuditLog."""

    class Meta(AbstractAuditLog.Meta):
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')
        indexes = [
            models.Index(
                fields=['entity_type', 'entity_id'],
                name='idx_audit_entity',
            ),
            models.Index(
                fields=['user', 'timestamp'],
                name='idx_audit_user_ts',
            ),
        ]


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------
class Notification(AbstractNotification):
    """Harbor notification — inherits from Keel's AbstractNotification."""

    class Meta(AbstractNotification.Meta):
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        indexes = [
            models.Index(
                fields=['recipient', 'is_read'],
                name='idx_notif_recip_read',
            ),
        ]


# ---------------------------------------------------------------------------
# NotificationPreference
# ---------------------------------------------------------------------------
class NotificationPreference(AbstractNotificationPreference):
    """Per-user notification channel preferences."""

    class Meta(AbstractNotificationPreference.Meta):
        verbose_name = _('Notification Preference')
        verbose_name_plural = _('Notification Preferences')


# ---------------------------------------------------------------------------
# NotificationLog
# ---------------------------------------------------------------------------
class NotificationLog(AbstractNotificationLog):
    """Tracks notification delivery per channel."""

    class Meta(AbstractNotificationLog.Meta):
        verbose_name = _('Notification Log')
        verbose_name_plural = _('Notification Logs')


# ---------------------------------------------------------------------------
# ArchivedRecord
# ---------------------------------------------------------------------------
class ArchivedRecord(models.Model):
    """Tracks archived records for data retention compliance.

    When records are archived, metadata is preserved here while the
    original data may be anonymized or moved to cold storage.
    """

    class EntityType(models.TextChoices):
        APPLICATION = 'application', _('Application')
        AWARD = 'award', _('Award')
        DRAWDOWN = 'drawdown', _('Drawdown Request')
        REPORT = 'report', _('Report')
        AUDIT_LOG = 'audit_log', _('Audit Log')
        TRANSACTION = 'transaction', _('Transaction')

    class RetentionPolicy(models.TextChoices):
        STANDARD = 'standard', _('Standard (7 years)')
        EXTENDED = 'extended', _('Extended (10 years)')
        PERMANENT = 'permanent', _('Permanent')
        FEDERAL = 'federal', _('Federal Requirement (3 years post-closeout)')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity_type = models.CharField(max_length=20, choices=EntityType.choices)
    entity_id = models.CharField(max_length=255)
    entity_description = models.TextField(blank=True)

    retention_policy = models.CharField(
        max_length=15,
        choices=RetentionPolicy.choices,
        default=RetentionPolicy.STANDARD,
    )

    original_created_at = models.DateTimeField(
        help_text=_('When the original record was created'),
    )
    archived_at = models.DateTimeField(auto_now_add=True)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='archived_records',
    )

    retention_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When this archived record can be permanently deleted'),
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Preserved metadata from the archived record'),
    )

    is_purged = models.BooleanField(
        default=False,
        help_text=_('Whether the original record has been purged from the system'),
    )
    purged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-archived_at']
        verbose_name = _('Archived Record')
        verbose_name_plural = _('Archived Records')
        indexes = [
            models.Index(
                fields=['entity_type', 'entity_id'],
                name='idx_archive_entity',
            ),
            models.Index(
                fields=['retention_expires_at'],
                name='idx_archive_expiry',
            ),
        ]

    def __str__(self):
        return f"Archived {self.get_entity_type_display()} - {self.entity_id}"


# ---------------------------------------------------------------------------
# OrganizationClaim
# ---------------------------------------------------------------------------
class OrganizationClaim(models.Model):
    """A user's request to be recognized as the primary contact for an organization."""

    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        APPROVED = 'approved', _('Approved')
        DENIED = 'denied', _('Denied')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='claims',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='organization_claims',
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_claims',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewer_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Organization Claim')
        verbose_name_plural = _('Organization Claims')
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'user'],
                condition=models.Q(status='pending'),
                name='unique_pending_claim_per_user_org',
            ),
        ]
        indexes = [
            models.Index(
                fields=['status', 'created_at'],
                name='idx_claim_status_created',
            ),
        ]

    def __str__(self):
        return f"{self.user} → {self.organization} ({self.get_status_display()})"


# ---------------------------------------------------------------------------
# OrganizationContact (assigned staff contact for high-priority orgs)
# ---------------------------------------------------------------------------
class OrganizationContact(models.Model):
    """Staff member assigned as the primary contact for an organization."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name='assigned_contact',
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='contact_assignments',
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contact_assignments_made',
    )
    notes = models.TextField(blank=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Organization Contact')
        verbose_name_plural = _('Organization Contacts')

    def __str__(self):
        return f"{self.assigned_to} → {self.organization}"
