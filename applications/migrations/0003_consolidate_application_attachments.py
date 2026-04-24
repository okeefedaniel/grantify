"""Consolidate ApplicationDocument + StaffDocument into ApplicationAttachment.

Four steps in order:

  1. Create ApplicationAttachment (extends
     ``keel.core.models.AbstractAttachment`` via an autodetected flat
     field list — the abstract's fields are expanded into the CreateModel
     because Django migrations materialize concrete subclass state).
  2. Data migration: copy every ApplicationDocument row into
     ApplicationAttachment with ``visibility='external'``, and every
     StaffDocument row with ``visibility='internal'``. The legacy
     ``document_type`` enum values carry over to the new free-text
     ``doc_category`` field (e.g. 'narrative', 'legal_review'). File
     paths are preserved verbatim — no physical file moves.
  3. Drop the legacy FKs on StaffDocument so Django can delete the
     tables cleanly.
  4. Delete the ApplicationDocument and StaffDocument models.

Harbor production was wiped on 2026-04-22 and has no rows to copy; the
demo environment may have some seeded rows. RunPython is a no-op when
the source tables are empty.
"""
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


def copy_documents_forward(apps, schema_editor):
    """Copy ApplicationDocument + StaffDocument into ApplicationAttachment."""
    ApplicationDocument = apps.get_model('applications', 'ApplicationDocument')
    StaffDocument = apps.get_model('applications', 'StaffDocument')
    ApplicationAttachment = apps.get_model('applications', 'ApplicationAttachment')

    for doc in ApplicationDocument.objects.all().iterator():
        file_name = doc.file.name if doc.file else ''
        ApplicationAttachment.objects.create(
            application_id=doc.application_id,
            file=file_name,
            filename=(file_name.rsplit('/', 1)[-1] if file_name else ''),
            content_type='',
            size_bytes=0,  # file.size triggers a storage access; skip for migration speed
            description=doc.description or '',
            visibility='external',
            source='upload',
            uploaded_by_id=doc.uploaded_by_id,
            manifest_packet_uuid='',
            title=doc.title or '',
            doc_category=doc.document_type or '',
        )

    for doc in StaffDocument.objects.all().iterator():
        file_name = doc.file.name if doc.file else ''
        ApplicationAttachment.objects.create(
            application_id=doc.application_id,
            file=file_name,
            filename=(file_name.rsplit('/', 1)[-1] if file_name else ''),
            content_type='',
            size_bytes=0,
            description=doc.description or '',
            visibility='internal',
            source='upload',
            uploaded_by_id=doc.uploaded_by_id,
            manifest_packet_uuid='',
            title=doc.title or '',
            doc_category=doc.document_type or '',
        )


def copy_documents_reverse(apps, schema_editor):
    """Reverse the data copy (legacy tables are gone post-migration so
    this just clears the new table)."""
    ApplicationAttachment = apps.get_model('applications', 'ApplicationAttachment')
    ApplicationAttachment.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0002_applicationassignment_align_with_keel_abstract'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Create the unified attachment table.
        migrations.CreateModel(
            name='ApplicationAttachment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('file', models.FileField(upload_to='attachments/%Y/%m/')),
                ('filename', models.CharField(blank=True, max_length=255)),
                ('content_type', models.CharField(blank=True, max_length=100)),
                ('size_bytes', models.PositiveBigIntegerField(default=0)),
                ('description', models.TextField(blank=True)),
                ('visibility', models.CharField(choices=[('external', 'External (applicant-visible)'), ('internal', 'Internal (staff-only)')], default='internal', max_length=10)),
                ('source', models.CharField(choices=[('upload', 'Manually uploaded'), ('manifest_signed', 'Signed document returned from Manifest'), ('system', 'System-generated')], default='upload', max_length=20)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('manifest_packet_uuid', models.CharField(blank=True, max_length=64)),
                ('title', models.CharField(blank=True, max_length=255)),
                ('doc_category', models.CharField(blank=True, help_text='Free-text category carried over from the pre-consolidation DocumentType enum (narrative / budget / legal_review / etc.). Optional — add TextChoices here if strict filtering is needed.', max_length=30)),
                ('application', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='applications.application')),
                ('uploaded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_uploaded', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Application Attachment',
                'verbose_name_plural': 'Application Attachments',
                'ordering': ['-uploaded_at'],
                'abstract': False,
            },
        ),

        # 2. Copy legacy rows into the new table.
        migrations.RunPython(copy_documents_forward, copy_documents_reverse),

        # 3. Remove legacy FK fields so the DeleteModel operations can
        #    succeed cleanly (Django's autogen put these first; we move
        #    them after the data copy so the source tables still exist
        #    during the RunPython step).
        migrations.RemoveField(
            model_name='staffdocument',
            name='application',
        ),
        migrations.RemoveField(
            model_name='staffdocument',
            name='uploaded_by',
        ),

        # 4. Drop legacy models.
        migrations.DeleteModel(
            name='ApplicationDocument',
        ),
        migrations.DeleteModel(
            name='StaffDocument',
        ),
    ]
