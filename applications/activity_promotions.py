"""Track A promotion rules for Harbor applications.

Maps audit-row creates of ApplicationAssignment / ApplicationAttachment /
ApplicationComment / ApplicationComplianceItem to activity verbs. Track B
verbs (workflow.transitioned for Application status changes, signing.* for
Manifest handoffs) emit explicitly from harbor's services / signal receivers
via record_activity().

ApplicationAssignment doubles as the "claim" gesture for Harbor — there's
no separate AbstractCollaborator model on harbor.Application (see
activity_models.py docstring). We promote ApplicationAssignment.create as
``collab.added`` (LEAD-equivalent) so the activity feed reads consistently
with peers that do have a collaborator model.
"""
from __future__ import annotations

import logging

from django.apps import apps

from keel.activity.registry import PromotionRegistry, PromotionRule

logger = logging.getLogger(__name__)


def _get_assignment(audit):
    Assignment = apps.get_model('applications', 'ApplicationAssignment')
    try:
        return (
            Assignment.objects.select_related('application', 'assigned_to')
            .get(pk=audit.entity_id)
        )
    except (Assignment.DoesNotExist, ValueError):
        return None


def _get_comment(audit):
    Comment = apps.get_model('applications', 'ApplicationComment')
    try:
        return (
            Comment.objects.select_related('application', 'author')
            .get(pk=audit.entity_id)
        )
    except (Comment.DoesNotExist, ValueError):
        return None


def _get_attachment(audit):
    Attachment = apps.get_model('applications', 'ApplicationAttachment')
    try:
        return Attachment.objects.select_related('application').get(pk=audit.entity_id)
    except (Attachment.DoesNotExist, ValueError):
        return None


def _get_compliance(audit):
    ComplianceItem = apps.get_model('applications', 'ApplicationComplianceItem')
    try:
        return ComplianceItem.objects.select_related('application').get(pk=audit.entity_id)
    except (ComplianceItem.DoesNotExist, ValueError):
        return None


# IMPORTANT: metadata_fn returns the metadata DICT ONLY (no model instances).
# The keel.activity registry stores the return value as the Activity.metadata
# JSONField, so any model instance in the returned dict will fail JSON encoding
# at insert time. The denormalized application FK on the Activity row is
# populated by Activity.save() (in activity_models.py) from the target GFK
# when target IS an Application -- no need to pass it through metadata_fn.

def _assignment_added_kwargs(audit):
    assignment = _get_assignment(audit)
    if assignment is None:
        return None
    return {
        'assignment_id': str(assignment.pk),
        'assigned_to': str(assignment.assigned_to_id) if assignment.assigned_to_id else '',
        'status': getattr(assignment, 'status', ''),
        'assignment_type': getattr(assignment, 'assignment_type', ''),
    }


def _comment_posted_kwargs(audit):
    comment = _get_comment(audit)
    if comment is None:
        return None
    return {
        'comment_id': str(comment.pk),
        'is_internal': bool(getattr(comment, 'is_internal', False)),
        'content_excerpt': str(getattr(comment, 'content', ''))[:80],
    }


def _attachment_uploaded_kwargs(audit):
    attachment = _get_attachment(audit)
    if attachment is None:
        return None
    return {
        'attachment_id': str(attachment.pk),
        'filename': str(getattr(attachment, 'file', '')).split('/')[-1] or '(file)',
        'visibility': getattr(attachment, 'visibility', ''),
        'document_type': getattr(attachment, 'document_type', ''),
    }


def _compliance_added_kwargs(audit):
    item = _get_compliance(audit)
    if item is None:
        return None
    return {
        'item_id': str(item.pk),
        'requirement_type': getattr(item, 'requirement_type', ''),
        'status': getattr(item, 'status', ''),
    }


def register_all() -> None:
    """Called from ApplicationsConfig.ready()."""
    # ApplicationAssignment as the "claim" gesture.
    PromotionRegistry.register(PromotionRule(
        entity_type='Application Assignment',
        action='create',
        verb='collab.added',
        visibility='collaborators',
        target_fn=lambda audit: getattr(_get_assignment(audit), 'application', None),
        action_fn=_get_assignment,
        deep_link_fn=lambda audit: _safe_get_url(getattr(_get_assignment(audit), 'application', None)),
        source_label_fn=_assignment_added_label,
        metadata_fn=_assignment_added_kwargs,
    ))

    PromotionRegistry.register(PromotionRule(
        entity_type='Application Assignment',
        action='delete',
        verb='collab.removed',
        visibility='collaborators',
        target_fn=lambda audit: _resolve_application_from_changes(audit),
        source_label_fn=lambda audit: f'{_actor_name(audit)} released an assignment',
        metadata_fn=lambda audit: {
            'status': (audit.changes or {}).get('status', ''),
        },
    ))

    PromotionRegistry.register(PromotionRule(
        entity_type='Application Comment',
        action='create',
        verb='diligence.note_posted',
        visibility=lambda audit: _comment_visibility(audit),
        target_fn=lambda audit: getattr(_get_comment(audit), 'application', None),
        action_fn=_get_comment,
        deep_link_fn=lambda audit: _safe_get_url(getattr(_get_comment(audit), 'application', None)),
        source_label_fn=lambda audit: f'{_actor_name(audit)} posted a comment',
        metadata_fn=_comment_posted_kwargs,
    ))

    PromotionRegistry.register(PromotionRule(
        entity_type='Application Attachment',
        action='create',
        verb='diligence.attachment_uploaded',
        visibility='collaborators',
        target_fn=lambda audit: getattr(_get_attachment(audit), 'application', None),
        action_fn=_get_attachment,
        deep_link_fn=lambda audit: _safe_get_url(getattr(_get_attachment(audit), 'application', None)),
        source_label_fn=lambda audit: f'{_actor_name(audit)} uploaded a file',
        metadata_fn=_attachment_uploaded_kwargs,
    ))

    PromotionRegistry.register(PromotionRule(
        entity_type='Compliance Item',
        action='create',
        verb='compliance.item_added',
        visibility='collaborators',
        target_fn=lambda audit: getattr(_get_compliance(audit), 'application', None),
        action_fn=_get_compliance,
        deep_link_fn=lambda audit: _safe_get_url(getattr(_get_compliance(audit), 'application', None)),
        source_label_fn=lambda audit: f'{_actor_name(audit)} added a compliance item',
        metadata_fn=_compliance_added_kwargs,
    ))

    logger.debug('keel.activity: harbor applications promotion rules registered (5 Track A rules)')


# Helpers

def _actor_name(audit) -> str:
    if audit.user_id is None:
        return 'system'
    return str(audit.user)


def _assignment_added_label(audit) -> str:
    assignment = _get_assignment(audit)
    if assignment is None:
        return f'{_actor_name(audit)} claimed an application'
    if assignment.assigned_to_id and assignment.assigned_to:
        invitee = assignment.assigned_to.get_full_name() or assignment.assigned_to.username
    else:
        invitee = 'someone'
    return f'{_actor_name(audit)} assigned {invitee} to process this application'


def _comment_visibility(audit):
    """Internal comments stay staff-only; external comments go to collaborators."""
    comment = _get_comment(audit)
    if comment is None:
        return 'collaborators'
    return 'staff' if getattr(comment, 'is_internal', False) else 'collaborators'


def _resolve_application_from_changes(audit):
    changes = audit.changes or {}
    app_id = changes.get('application_id') or changes.get('application')
    if not app_id:
        return None
    Application = apps.get_model('applications', 'Application')
    try:
        return Application.objects.get(pk=app_id)
    except (Application.DoesNotExist, ValueError, TypeError):
        return None


def _safe_get_url(obj) -> str:
    if obj is None:
        return ''
    try:
        return obj.get_absolute_url() or ''
    except Exception:
        return ''
