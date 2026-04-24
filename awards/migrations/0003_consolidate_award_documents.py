"""Consolidate AwardDocument into AwardAttachment.

Three steps in order:

  1. Add ``title`` + ``doc_category`` fields to AwardAttachment so it
     can absorb AwardDocument's shape.
  2. Data migration: copy every AwardDocument row into AwardAttachment
     with ``source=UPLOAD`` and the legacy ``document_type`` enum value
     carried over to ``doc_category`` verbatim. File paths are
     preserved (no physical file moves).
  3. Delete the AwardDocument model.

Harbor production was wiped on 2026-04-22 so the data copy is a no-op
there; demo data (if any) carries forward.
"""
from django.db import migrations, models


def copy_documents_forward(apps, schema_editor):
    AwardDocument = apps.get_model('awards', 'AwardDocument')
    AwardAttachment = apps.get_model('awards', 'AwardAttachment')

    for doc in AwardDocument.objects.all().iterator():
        file_name = doc.file.name if doc.file else ''
        AwardAttachment.objects.create(
            award_id=doc.award_id,
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
    AwardAttachment = apps.get_model('awards', 'AwardAttachment')
    # Reverse only clears uploads (not Manifest-signed rows) since
    # AwardDocument itself is gone by then.
    AwardAttachment.objects.filter(source='upload').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('awards', '0002_awardattachment'),
    ]

    operations = [
        # 1. Add the fields that AwardAttachment needs to absorb
        #    AwardDocument's shape.
        migrations.AddField(
            model_name='awardattachment',
            name='title',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='awardattachment',
            name='doc_category',
            field=models.CharField(
                blank=True,
                help_text=(
                    'Free-text category carried over from the pre-consolidation '
                    'DocumentType enum (agreement / amendment / correspondence / '
                    'report / other).'
                ),
                max_length=30,
            ),
        ),

        # 2. Copy legacy rows.
        migrations.RunPython(copy_documents_forward, copy_documents_reverse),

        # 3. Drop the legacy model.
        migrations.DeleteModel(
            name='AwardDocument',
        ),
    ]
