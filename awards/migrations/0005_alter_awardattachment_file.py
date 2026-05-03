"""Apply FileSecurityValidator to awardattachment.file (keel 0.25.0+).

Auto-generated to record the AbstractAttachment.file change in keel —
keel/core/models.py now sets validators=[FileSecurityValidator()].
"""
from django.db import migrations, models

import keel.security.scanning


class Migration(migrations.Migration):

    dependencies = [
        ('awards', '0004_fund_source'),
    ]

    operations = [
        migrations.AlterField(
            model_name='awardattachment',
            name='file',
            field=models.FileField(
                upload_to='attachments/%Y/%m/',
                validators=[keel.security.scanning.FileSecurityValidator()],
            ),
        ),
    ]
