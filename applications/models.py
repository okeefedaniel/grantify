import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


from keel.core.models import (
    AbstractAssignment,
    AbstractAttachment,
    AbstractInternalNote,
    AbstractStatusHistory,
)

from core.validators import validate_document_file


class Application(models.Model):
    """A grant application submitted by an organization for a grant program."""

    COMMS_PRODUCT = 'harbor'
    COMMS_ENTITY_TYPE = 'application'

    def comms_display_name(self):
        return f'Harbor \u2013 {self.project_title[:60]}'

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        SUBMITTED = 'submitted', _('Submitted')
        UNDER_REVIEW = 'under_review', _('Under Review')
        REVISION_REQUESTED = 'revision_requested', _('Revision Requested')
        APPROVED = 'approved', _('Approved')
        DENIED = 'denied', _('Denied')
        WITHDRAWN = 'withdrawn', _('Withdrawn')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grant_program = models.ForeignKey(
        'grants.GrantProgram',
        on_delete=models.PROTECT,
        related_name='applications',
    )
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='applications',
    )
    organization = models.ForeignKey(
        'harbor_core.Organization',
        on_delete=models.PROTECT,
        related_name='applications',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    submitted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    # Project details
    project_title = models.CharField(max_length=500)
    project_description = models.TextField()
    requested_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text=_('Amount of funding requested'),
    )
    proposed_start_date = models.DateField()
    proposed_end_date = models.DateField()

    # Match information
    match_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Proposed matching contribution amount'),
    )
    match_description = models.TextField(
        blank=True,
        default='',
        help_text=_('Description of matching funds or in-kind contributions'),
    )

    # Versioning
    version = models.IntegerField(default=1)
    version_notes = models.TextField(blank=True, default='')

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Application')
        verbose_name_plural = _('Applications')

    def __str__(self):
        return f"{self.project_title} - {self.organization}"

    def get_absolute_url(self):
        return reverse('applications:detail', kwargs={'pk': self.pk})

    @property
    def is_editable(self):
        """Return True if the application can still be edited."""
        return self.status in (self.Status.DRAFT, self.Status.REVISION_REQUESTED)


class ApplicationSection(models.Model):
    """A section within an application, storing flexible form data as JSON."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='sections',
    )
    section_name = models.CharField(max_length=255)
    section_order = models.IntegerField(default=0)
    content = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Flexible form data stored as JSON'),
    )
    is_complete = models.BooleanField(default=False)

    class Meta:
        ordering = ['section_order']
        unique_together = [('application', 'section_order')]
        verbose_name = _('Application Section')
        verbose_name_plural = _('Application Sections')

    def __str__(self):
        return f"{self.application.project_title} - {self.section_name}"


class ApplicationAttachment(AbstractAttachment):
    """Documents attached to an application, unified across applicant- and
    staff-facing uploads.

    Consolidates the pre-0.13 ApplicationDocument (applicant-visible) and
    StaffDocument (staff-only) models into one. The abstract's
    ``visibility`` field is the applicant/staff split — EXTERNAL for
    applicant-uploaded materials, INTERNAL for staff-only docs (legal
    review, site visit reports, etc.). Also the destination for signed
    PDFs returning from the Manifest roundtrip
    (source=MANIFEST_SIGNED).

    Two product-local additions on top of AbstractAttachment:

    * ``title`` — human-readable label (the abstract has ``description``
      but harbor's UI treats ``title`` as the primary display field and
      ``description`` as optional long-form context).
    * ``doc_category`` — free-text carryover of the old DocumentType
      enum values ('narrative', 'budget', 'legal_review', etc.). Kept
      as free-text rather than a TextChoices because the two source
      enums were disjoint; teams can add TextChoices later if filtering
      warrants it.
    """

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='attachments',
    )
    title = models.CharField(max_length=255, blank=True)
    doc_category = models.CharField(
        max_length=30, blank=True,
        help_text=_(
            'Free-text category carried over from the pre-consolidation '
            'DocumentType enum (narrative / budget / legal_review / etc.). '
            'Optional — add TextChoices here if strict filtering is needed.'
        ),
    )

    class Meta(AbstractAttachment.Meta):
        verbose_name = _('Application Attachment')
        verbose_name_plural = _('Application Attachments')

    def __str__(self):
        label = self.title or self.filename or 'Attachment'
        return f"{label} ({self.get_visibility_display()})"


def _app_attachments_external(application):
    """Backward-compat accessor for ``application.documents``.

    Pre-consolidation: ``application.documents`` was the reverse-FK
    queryset of ApplicationDocument (applicant-visible). Post-
    consolidation: returns the same user-facing set via the unified
    ApplicationAttachment table, filtered to EXTERNAL visibility.
    Preserves all existing template and view call sites that read
    ``application.documents``.
    """
    return application.attachments.filter(
        visibility=ApplicationAttachment.Visibility.EXTERNAL,
    )


def _app_attachments_internal(application):
    """Backward-compat accessor for ``application.staff_documents``."""
    return application.attachments.filter(
        visibility=ApplicationAttachment.Visibility.INTERNAL,
    )


Application.add_to_class('documents', property(_app_attachments_external))
Application.add_to_class('staff_documents', property(_app_attachments_internal))


class ApplicationComment(AbstractInternalNote):
    """Comments on an application, with support for internal staff-only notes.

    Inherits from Keel's AbstractInternalNote which provides:
    id, author, content, is_internal, created_at, updated_at.

    Harbor convention: is_internal defaults to False (external users can see
    comments) — overridden from the abstract's default of True.
    """

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='comments',
    )
    is_internal = models.BooleanField(
        default=False,
        help_text=_('If True, this comment is visible only to staff reviewers'),
    )

    class Meta(AbstractInternalNote.Meta):
        verbose_name = _('Application Comment')
        verbose_name_plural = _('Application Comments')

    def __str__(self):
        visibility = 'Internal' if self.is_internal else 'Public'
        return f"Comment by {self.author} ({visibility}) on {self.application}"


class ApplicationComplianceItem(models.Model):
    """Pre-award due-diligence checklist item for an application.

    Each item represents a compliance requirement that must be verified
    by agency staff before the application can be approved.  Items are
    created automatically when an application is submitted and can be
    toggled via the application detail page.
    """

    class ItemType(models.TextChoices):
        SAM_REGISTRATION = 'sam_registration', _('SAM Registration Active')
        TAX_EXEMPT = 'tax_exempt', _('Tax-Exempt Status Verified')
        AUDIT_CLEARANCE = 'audit_clearance', _('Audit Clearance')
        DEBARMENT_CHECK = 'debarment_check', _('Debarment / Suspension Check')
        BUDGET_REVIEW = 'budget_review', _('Budget Review Complete')
        NARRATIVE_REVIEW = 'narrative_review', _('Narrative Review Complete')
        INSURANCE_VERIFIED = 'insurance_verified', _('Insurance Verification')
        MATCH_VERIFIED = 'match_verified', _('Match Funds Verified')
        CONFLICT_OF_INTEREST = 'conflict_of_interest', _('Conflict of Interest Check')
        ELIGIBILITY_CONFIRMED = 'eligibility_confirmed', _('Eligibility Confirmed')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='compliance_items',
    )
    item_type = models.CharField(
        max_length=30,
        choices=ItemType.choices,
    )
    label = models.CharField(
        max_length=255,
        help_text=_('Human-readable description of the compliance requirement'),
    )
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_compliance_items',
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(
        blank=True,
        default='',
        help_text=_('Staff notes about this compliance item'),
    )
    is_required = models.BooleanField(
        default=True,
        help_text=_('Whether this item must be verified before approval'),
    )

    class Meta:
        ordering = ['item_type']
        unique_together = [('application', 'item_type')]
        verbose_name = _('Application Compliance Item')
        verbose_name_plural = _('Application Compliance Items')

    def __str__(self):
        status = 'Verified' if self.is_verified else 'Pending'
        return f"{self.label} ({status})"


class ApplicationStatusHistory(AbstractStatusHistory):
    """Audit trail of status changes for an application.

    Inherits from Keel's AbstractStatusHistory which provides:
    id, old_status, new_status, changed_by, comment, changed_at.
    """

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='status_history',
    )

    class Meta(AbstractStatusHistory.Meta):
        verbose_name = _('Application Status History')
        verbose_name_plural = _('Application Status Histories')

    def __str__(self):
        return f"{self.application}: {self.old_status} -> {self.new_status}"


class ApplicationAssignment(AbstractAssignment):
    """Assignment of internal staff to process/work on an application.

    Extends keel.core.models.AbstractAssignment (canonical CLAIMED vs
    MANAGER_ASSIGNED types; ASSIGNED / IN_PROGRESS / COMPLETED /
    REASSIGNED / RELEASED status machine). Distinct from ReviewAssignment
    (formal scoring with rubrics).

    Field renames from the pre-0.13 bespoke version, aligned with the
    abstract's naming:

      * ``assigned_at``  → ``claimed_at`` (auto_now_add; unchanged semantics)
      * ``completed_at`` → ``released_at`` (nullable; now also set on
        REASSIGNED / RELEASED, not only on COMPLETED)

    The ``updated_at`` field was dropped — the abstract does not expose
    one and nothing in harbor queried it.
    """

    application = models.ForeignKey(
        'Application',
        on_delete=models.CASCADE,
        related_name='staff_assignments',
    )

    class Meta(AbstractAssignment.Meta):
        verbose_name = _('Application Assignment')
        verbose_name_plural = _('Application Assignments')

    def __str__(self):
        return (
            f"{self.assigned_to} \u2192 {self.application} "
            f"({self.get_status_display()})"
        )
