"""Apply FileSecurityValidator to applicationattachment.file (keel 0.25.0+).

Auto-generated to record the AbstractAttachment.file change in keel —
keel/core/models.py now sets validators=[FileSecurityValidator()].
"""
from django.db import migrations, models

import keel.security.scanning


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0003_consolidate_application_attachments'),
    ]

    operations = [
        migrations.AlterField(
            model_name='applicationattachment',
            name='file',
            field=models.FileField(
                upload_to='attachments/%Y/%m/',
                validators=[keel.security.scanning.FileSecurityValidator()],
            ),
        ),
    ]
