"""Manifest roundtrip receiver for Award.

When a ``ManifestHandoff`` completes — via the inbound Manifest webhook
at ``/keel/signatures/webhook/`` or via
``keel.signatures.client.local_sign`` (standalone-mode fallback) —
``keel.signatures`` fires ``packet_approved``. The receiver:

  1. Writes the signed PDF to the award's ``attachments`` collection
     as an ``AwardAttachment(source=MANIFEST_SIGNED)`` with
     ``manifest_packet_uuid`` filled in.
  2. Transitions ``Award.status`` to ``EXECUTED`` (the handoff's
     ``on_approved_status``) and stamps ``executed_at = now()``.
  3. Updates the legacy ``SignatureRequest`` row so existing
     templates/queries keep showing the completion state. The
     SignatureRequest model is retained for backward compatibility
     during the DocuSign→Manifest cutover window and will be dropped
     in a follow-up once no legacy data references it.

Downstream receivers (notifications, reporting) can attach to the same
signal independently.
"""
import logging

from django.apps import apps
from django.core.files.base import ContentFile
from django.dispatch import receiver
from django.utils import timezone

from keel.signatures.signals import packet_approved

logger = logging.getLogger(__name__)


@receiver(packet_approved)
def on_packet_approved(sender, handoff, source_obj, signed_pdf, **kwargs):
    """File the signed PDF on the award + transition status."""
    if not hasattr(source_obj, '_meta'):
        return
    if source_obj._meta.label_lower != 'awards.award':
        return

    try:
        attachment_cls = apps.get_model(*handoff.attachment_model.split('.'))
    except (LookupError, ValueError):
        logger.exception(
            'Unknown attachment model %r on handoff %s',
            handoff.attachment_model, handoff.pk,
        )
        return

    if hasattr(signed_pdf, 'read'):
        raw = signed_pdf.read()
        filename = (
            getattr(signed_pdf, 'name', None)
            or f'{handoff.packet_label or "signed"}.pdf'
        )
    else:
        raw = bytes(signed_pdf)
        filename = f'{handoff.packet_label or "signed"}.pdf'
    filename = filename.rsplit('/', 1)[-1] or 'signed.pdf'

    attachment_cls.objects.create(
        **{handoff.attachment_fk_name: source_obj},
        file=ContentFile(raw, name=filename),
        filename=filename,
        content_type='application/pdf',
        size_bytes=len(raw),
        description=handoff.packet_label or 'Signed award agreement via Manifest',
        visibility='internal',
        source='manifest_signed',
        manifest_packet_uuid=handoff.manifest_packet_uuid,
        uploaded_by=handoff.created_by,
    )

    target = handoff.on_approved_status or 'executed'
    now = timezone.now()
    if source_obj.status != target:
        source_obj.status = target
        update_fields = ['status', 'updated_at']
        if not source_obj.executed_at:
            source_obj.executed_at = now
            update_fields.append('executed_at')
        try:
            source_obj.save(update_fields=update_fields)
        except Exception:
            logger.exception(
                'Failed to transition Award %s → %s after handoff %s',
                source_obj.pk, target, handoff.pk,
            )

    # Reconcile the legacy SignatureRequest row so award_detail
    # templates + signature_status endpoints still show completion.
    # Match by manifest_packet_uuid stored in envelope_id at send time.
    try:
        from .models import SignatureRequest
        sig = SignatureRequest.objects.filter(
            award=source_obj,
            envelope_id=handoff.manifest_packet_uuid or str(handoff.pk),
        ).first()
        if sig and sig.status != SignatureRequest.Status.SIGNED:
            sig.status = SignatureRequest.Status.SIGNED
            sig.completed_at = now
            sig.save(update_fields=['status', 'completed_at', 'updated_at'])
    except Exception:
        logger.exception(
            'Failed to reconcile SignatureRequest for award %s handoff %s',
            source_obj.pk, handoff.pk,
        )
