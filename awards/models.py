import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from keel.core.models import AbstractAttachment

from core.validators import validate_document_file


# ---------------------------------------------------------------------------
# Award
# ---------------------------------------------------------------------------
class Award(models.Model):
    """Grant award issued to a recipient after application approval."""

    class FundSource(models.TextChoices):
        """Federal/state fund-source taxonomy.

        MUST stay value-aligned with helm.tasks.models.Project.FundSource —
        Helm's `_fund_source_rollup` joins by string value. When this enum
        changes, mirror the change in Helm or the join breaks silently.
        """
        ARPA = 'arpa', _('ARPA — American Rescue Plan Act')
        IIJA = 'iija', _('IIJA — Infrastructure Investment and Jobs Act')
        IRA = 'ira', _('IRA — Inflation Reduction Act')
        BEAD = 'bead', _('BEAD — Broadband Equity, Access, and Deployment')
        SLCGP = 'slcgp', _('SLCGP — State and Local Cybersecurity Grant')
        CDBG = 'cdbg', _('CDBG — Community Development Block Grant')
        GO_BOND = 'go_bond', _('General Obligation Bond')
        REVENUE_BOND = 'revenue_bond', _('Revenue Bond')
        STATE_MATCH = 'state_match', _('State Match')
        LOCAL_MATCH = 'local_match', _('Local Match')
        GENERAL_FUND = 'general_fund', _('General Fund')

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        PENDING_APPROVAL = 'pending_approval', _('Pending Approval')
        APPROVED = 'approved', _('Approved')
        EXECUTED = 'executed', _('Executed')
        ACTIVE = 'active', _('Active')
        ON_HOLD = 'on_hold', _('On Hold')
        COMPLETED = 'completed', _('Completed')
        TERMINATED = 'terminated', _('Terminated')
        CANCELLED = 'cancelled', _('Cancelled')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.OneToOneField(
        'applications.Application',
        on_delete=models.CASCADE,
        related_name='award',
    )
    grant_program = models.ForeignKey(
        'grants.GrantProgram',
        on_delete=models.CASCADE,
        related_name='awards',
    )
    agency = models.ForeignKey(
        'harbor_core.Agency',
        on_delete=models.CASCADE,
        related_name='awards',
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='awards_received',
    )
    organization = models.ForeignKey(
        'harbor_core.Organization',
        on_delete=models.CASCADE,
        related_name='awards',
    )

    award_number = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    award_amount = models.DecimalField(max_digits=15, decimal_places=2)
    fund_source = models.CharField(
        max_length=20,
        choices=FundSource.choices,
        blank=True,
        db_index=True,
        help_text=_(
            'Federal/state fund source. Used by Helm to join Harbor drawdown '
            'data into its CIP fund-source rollup. Leave blank when not applicable.'
        ),
    )
    award_date = models.DateField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True, db_index=True)

    terms_and_conditions = models.TextField()
    special_conditions = models.TextField(blank=True)

    requires_match = models.BooleanField(default=False)
    match_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_awards',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    executed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Award')
        verbose_name_plural = _('Awards')

    def __str__(self):
        return f"{self.award_number} - {self.title}"


# ---------------------------------------------------------------------------
# AwardAmendment
# ---------------------------------------------------------------------------
class AwardAmendment(models.Model):
    """Formal modification to an existing award."""

    class AmendmentType(models.TextChoices):
        BUDGET_MODIFICATION = 'budget_modification', _('Budget Modification')
        TIME_EXTENSION = 'time_extension', _('Time Extension')
        SCOPE_CHANGE = 'scope_change', _('Scope Change')
        PERSONNEL_CHANGE = 'personnel_change', _('Personnel Change')
        OTHER = 'other', _('Other')

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        SUBMITTED = 'submitted', _('Submitted')
        APPROVED = 'approved', _('Approved')
        DENIED = 'denied', _('Denied')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    award = models.ForeignKey(
        Award,
        on_delete=models.CASCADE,
        related_name='amendments',
    )
    amendment_number = models.IntegerField()
    amendment_type = models.CharField(
        max_length=25,
        choices=AmendmentType.choices,
    )
    description = models.TextField()
    old_value = models.JSONField(default=dict)
    new_value = models.JSONField(default=dict)

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='requested_amendments',
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_amendments',
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['award', 'amendment_number']
        verbose_name = _('Award Amendment')
        verbose_name_plural = _('Award Amendments')

    def __str__(self):
        return f"{self.award.award_number} - Amendment #{self.amendment_number}"


# ---------------------------------------------------------------------------
# AwardDocument
# ---------------------------------------------------------------------------
class AwardAttachment(AbstractAttachment):
    """Unified attachment collection on an Award.

    Consolidates the historical AwardDocument (typed agreement /
    amendment / correspondence / report uploads) and the Manifest-signed
    PDF destination into a single table. ``source`` distinguishes
    manually-uploaded documents from signed PDFs returning from the
    Manifest roundtrip (``source=MANIFEST_SIGNED`` with
    ``manifest_packet_uuid`` populated).

    Two product-local additions on top of AbstractAttachment (mirroring
    ApplicationAttachment):

    * ``title`` — primary display label.
    * ``doc_category`` — free-text carryover of the pre-consolidation
      AwardDocument.DocumentType enum values ('agreement', 'amendment',
      'correspondence', 'report', 'other').
    """

    award = models.ForeignKey(
        Award, on_delete=models.CASCADE, related_name='attachments',
    )
    title = models.CharField(max_length=255, blank=True)
    doc_category = models.CharField(
        max_length=30, blank=True,
        help_text=_(
            'Free-text category carried over from the pre-consolidation '
            'DocumentType enum (agreement / amendment / correspondence / '
            'report / other).'
        ),
    )

    class Meta(AbstractAttachment.Meta):
        verbose_name = _('Award Attachment')
        verbose_name_plural = _('Award Attachments')


def _award_documents_accessor(award):
    """Backward-compat accessor for ``award.documents``.

    Pre-consolidation this was the reverse-FK queryset of AwardDocument.
    Post-consolidation returns the same user-facing set via the unified
    AwardAttachment table — all attachments including Manifest-signed
    PDFs. Filtering by source='upload' would hide signed docs; templates
    historically showed both, so we return everything.
    """
    return award.attachments.all()


Award.add_to_class('documents', property(_award_documents_accessor))


# ---------------------------------------------------------------------------
# SubRecipient
# ---------------------------------------------------------------------------
class SubRecipient(models.Model):
    """Sub-recipient/sub-grantee receiving pass-through funds from a primary award."""

    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        INACTIVE = 'inactive', _('Inactive')
        SUSPENDED = 'suspended', _('Suspended')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    award = models.ForeignKey(Award, on_delete=models.CASCADE, related_name='sub_recipients')
    organization = models.ForeignKey('harbor_core.Organization', on_delete=models.PROTECT, related_name='sub_recipient_awards')
    contact_name = models.CharField(max_length=255)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20, blank=True)
    sub_award_amount = models.DecimalField(max_digits=15, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    scope_of_work = models.TextField()
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.ACTIVE)
    risk_level = models.CharField(max_length=10, choices=[('low', _('Low')), ('medium', _('Medium')), ('high', _('High'))], default='low')
    monitoring_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['organization__name']
        verbose_name = _('Sub-Recipient')
        verbose_name_plural = _('Sub-Recipients')

    def __str__(self):
        return f"{self.organization.name} - {self.award.award_number}"


# ---------------------------------------------------------------------------
# PerformanceMetric
# ---------------------------------------------------------------------------
class PerformanceMetric(models.Model):
    """Tracks performance outcomes and KPIs for an award."""

    class MetricType(models.TextChoices):
        OUTPUT = 'output', _('Output')
        OUTCOME = 'outcome', _('Outcome')
        EFFICIENCY = 'efficiency', _('Efficiency')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    award = models.ForeignKey(Award, on_delete=models.CASCADE, related_name='performance_metrics')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    metric_type = models.CharField(max_length=15, choices=MetricType.choices, default=MetricType.OUTPUT)
    target_value = models.DecimalField(max_digits=15, decimal_places=2)
    actual_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    unit_of_measure = models.CharField(max_length=100, help_text=_('e.g. people served, jobs created'))
    reporting_period = models.CharField(max_length=50, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['award', 'name']
        verbose_name = _('Performance Metric')
        verbose_name_plural = _('Performance Metrics')

    def __str__(self):
        return f"{self.award.award_number} - {self.name}"

    @property
    def percent_achieved(self):
        if self.target_value and self.actual_value:
            return round((self.actual_value / self.target_value) * 100, 1)
        return 0


# ---------------------------------------------------------------------------
# SignatureRequest  (DocuSign e-Signature)
# ---------------------------------------------------------------------------
class SignatureRequest(models.Model):
    """Tracks a DocuSign e-signature request for an award agreement."""

    class Status(models.TextChoices):
        SENT = 'sent', _('Sent')
        DELIVERED = 'delivered', _('Delivered')
        SIGNED = 'signed', _('Signed')
        DECLINED = 'declined', _('Declined')
        VOIDED = 'voided', _('Voided')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    award = models.ForeignKey(Award, on_delete=models.CASCADE, related_name='signature_requests')
    envelope_id = models.CharField(max_length=100, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SENT)
    signer_name = models.CharField(max_length=255)
    signer_email = models.EmailField()
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_signatures',
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    signed_document = models.FileField(upload_to='awards/signed/', null=True, blank=True, validators=[validate_document_file])
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-sent_at']
        verbose_name = _('Signature Request')
        verbose_name_plural = _('Signature Requests')

    def __str__(self):
        return f"Signature for {self.award.award_number} - {self.get_status_display()}"
