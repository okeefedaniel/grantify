"""Align ApplicationAssignment with keel.core.models.AbstractAssignment.

Field renames:
  * assigned_at  -> claimed_at
  * completed_at -> released_at

Field drop:
  * updated_at — the abstract does not expose one; nothing queries it.

Schema changes:
  * status widens max_length 15 -> 20 and adds the RELEASED choice.
  * assignment_type choices + help text normalised to the abstract's.
  * Model ``ordering`` stays the same (the abstract already uses -claimed_at).
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='applicationassignment',
            old_name='assigned_at',
            new_name='claimed_at',
        ),
        migrations.RenameField(
            model_name='applicationassignment',
            old_name='completed_at',
            new_name='released_at',
        ),
        migrations.RemoveField(
            model_name='applicationassignment',
            name='updated_at',
        ),
        migrations.AlterField(
            model_name='applicationassignment',
            name='status',
            field=models.CharField(
                choices=[
                    ('assigned', 'Assigned'),
                    ('in_progress', 'In progress'),
                    ('completed', 'Completed'),
                    ('reassigned', 'Reassigned'),
                    ('released', 'Released back to pool'),
                ],
                default='assigned',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='applicationassignment',
            name='assignment_type',
            field=models.CharField(
                choices=[
                    ('claimed', 'Self-claimed'),
                    ('manager_assigned', 'Manager-assigned'),
                ],
                default='claimed',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='applicationassignment',
            name='notes',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='applicationassignment',
            name='assigned_by',
            field=models.ForeignKey(
                blank=True,
                help_text='Manager who made the assignment; null for self-claims.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='%(app_label)s_%(class)s_delegated',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='applicationassignment',
            name='assigned_to',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='%(app_label)s_%(class)s_assigned',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterModelOptions(
            name='applicationassignment',
            options={
                'ordering': ['-claimed_at'],
                'verbose_name': 'Application Assignment',
                'verbose_name_plural': 'Application Assignments',
            },
        ),
    ]
