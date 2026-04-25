"""
Drop orphan tables and migration history left in harbor's prod DB by
sibling-product demo services that were misconfigured to use harbor's
Postgres. Those services (lookout-demo, admiralty-demo, manifest-demo,
purser-demo, plus historically bounty-demo) have all been repointed at
their own product's `demo` database.

This migration is a no-op against any DB that doesn't already have the
orphan tables / migration rows (e.g. harbor's `demo` DB, fresh deploys,
or self-hosted customer instances).
"""

from django.db import migrations


ORPHAN_TABLES = [
    # bills (lookout)
    'bills_bill', 'bills_billhistory', 'bills_billsponsor', 'bills_billtext',
    'bills_billvote', 'bills_committee',
    # calendar_app (lookout)
    'calendar_app_deadline', 'calendar_app_hearingdate', 'calendar_app_sessionmilestone',
    # discover (lookout)
    'discover_committeemembership', 'discover_discoverconversation',
    'discover_discovermessage', 'discover_legislativesession',
    # foia (admiralty)
    'foia_foiaappeal', 'foia_foiadetermination',
    'foia_foiadetermination_exemptions_claimed', 'foia_foiadocument',
    'foia_foiarequest', 'foia_foiarequeststatushistory', 'foia_foiaresponsepackage',
    'foia_foiascope', 'foia_foiasearchresult', 'foia_statutoryexemption',
    # integration (bounty)
    'integration_harborconnection',
    # keel.compliance (purser)
    'keel_compliance_complianceitem', 'keel_compliance_complianceobligation',
    'keel_compliance_compliancetemplate',
    # keel.periods (purser)
    'keel_periods_fiscalperiod', 'keel_periods_fiscalyear',
    # keel.reporting (purser)
    'keel_reporting_reportlineitem', 'keel_reporting_reportschema',
    # lookout_core (lookout)
    'lookout_core_auditlog', 'lookout_core_lookoutprofile', 'lookout_core_notification',
    'lookout_core_notificationlog', 'lookout_core_notificationpreference',
    # signing (lookout)
    'signing_signingflow', 'signing_signingstep',
    # stakeholders (lookout)
    'stakeholders_legislator', 'stakeholders_stakeholder',
    'stakeholders_stakeholderinteraction',
    # testimony (lookout)
    'testimony_testimony', 'testimony_testimonyattachment', 'testimony_testimonycomment',
    'testimony_testimonystakeholder', 'testimony_testimonystatushistory',
    'testimony_testimonytemplate', 'testimony_testimonyversion',
    # tracking (lookout)
    'tracking_billattachment', 'tracking_billcollaborator', 'tracking_testimonyarchive',
    'tracking_trackedbill', 'tracking_trackedbillstatushistory', 'tracking_trackingnote',
    # watchlist (lookout)
    'watchlist_alertrule', 'watchlist_relevancescore', 'watchlist_watchfreetext',
    'watchlist_watchkeyword', 'watchlist_watchprofile',
]

ORPHAN_MIGRATION_APPS = [
    'bills', 'calendar_app', 'discover', 'foia', 'integration',
    'keel_compliance', 'keel_periods', 'keel_reporting', 'keel_search',
    'lookout_core', 'signing', 'stakeholders', 'testimony', 'tracking',
    'watchlist',
]


def drop_orphan_migration_rows(apps, schema_editor):
    schema_editor.execute(
        "DELETE FROM django_migrations WHERE app = ANY(%s)",
        [ORPHAN_MIGRATION_APPS],
    )


def noop_reverse(apps, schema_editor):
    """Reverse is a no-op: we cannot recreate dropped tables."""


class Migration(migrations.Migration):

    dependencies = [
        ('harbor_core', '0004_remove_harborprofile_anthropic_api_key'),
    ]

    operations = [
        migrations.RunSQL(
            sql='\n'.join(
                f'DROP TABLE IF EXISTS "{t}" CASCADE;' for t in ORPHAN_TABLES
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunPython(drop_orphan_migration_rows, reverse_code=noop_reverse),
    ]
