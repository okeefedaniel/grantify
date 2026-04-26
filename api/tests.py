"""Tests for Harbor's helm-feed endpoints."""
import os
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from applications.models import Application
from awards.models import Award
from core.models import Agency, Organization
from financial.models import DrawdownRequest, Transaction
from grants.models import FundingSource, GrantProgram

from .helm_feed import _fund_source_breakdown

User = get_user_model()

TEST_PASSWORD = os.environ.get('TEST_PASSWORD', 'test' + 'pass123!')


class FundSourceBreakdownTests(TestCase):
    """Verify the per-fund-source aggregation that Helm joins against."""

    def setUp(self):
        from core.test_helpers import create_test_user

        self.agency = Agency.objects.create(name='CT DECD', abbreviation='DECD')
        self.org = Organization.objects.create(name='Town of Branford', org_type='municipality')
        self.user = create_test_user(
            username='admin', role='admin', agency=self.agency,
            password=TEST_PASSWORD,
        )
        self.fs = FundingSource.objects.create(name='ARPA', source_type='federal')
        self.gp = GrantProgram.objects.create(
            agency=self.agency, title='ARPA Bridge Program',
            description='Bridges', funding_source=self.fs,
            total_funding=Decimal('5000000'),
            min_award=Decimal('100000'), max_award=Decimal('1000000'),
            fiscal_year='2025-2026', duration_months=12,
            application_deadline=timezone.now() + timedelta(days=30),
            posting_date=timezone.now(), created_by=self.user,
        )

    def _make_award(self, *, fund_source, amount, award_number):
        app = Application.objects.create(
            grant_program=self.gp, applicant=self.user, organization=self.org,
            project_title=f'Project {award_number}',
            project_description='Desc',
            requested_amount=Decimal(str(amount)),
            proposed_start_date=date.today(),
            proposed_end_date=date.today() + timedelta(days=365),
            status=Application.Status.APPROVED,
        )
        return Award.objects.create(
            application=app, grant_program=self.gp, agency=self.agency,
            recipient=self.user, organization=self.org,
            award_number=award_number, title=f'Award {award_number}',
            award_amount=Decimal(str(amount)),
            fund_source=fund_source,
            terms_and_conditions='Standard.',
            status=Award.Status.ACTIVE,
        )

    def test_breakdown_buckets_awards_by_fund_source(self):
        a1 = self._make_award(fund_source='arpa', amount=240000, award_number='A1')
        a2 = self._make_award(fund_source='arpa', amount=160000, award_number='A2')
        a3 = self._make_award(fund_source='iija', amount=500000, award_number='A3')

        active = Award.objects.filter(status__in=['active', 'executed'])
        out = _fund_source_breakdown(active)

        self.assertEqual(out['arpa']['award_count'], 2)
        self.assertEqual(out['arpa']['award_value_cents'], 40000000)  # $400k * 100
        self.assertEqual(out['iija']['award_count'], 1)
        self.assertEqual(out['iija']['award_value_cents'], 50000000)  # $500k * 100

    def test_breakdown_groups_unspecified_fund_source(self):
        self._make_award(fund_source='', amount=100000, award_number='A1')
        active = Award.objects.filter(status__in=['active', 'executed'])
        out = _fund_source_breakdown(active)
        self.assertIn('unspecified', out)
        self.assertEqual(out['unspecified']['award_count'], 1)

    def test_breakdown_sums_paid_drawdowns_per_fund_source(self):
        a1 = self._make_award(fund_source='arpa', amount=400000, award_number='A1')
        DrawdownRequest.objects.create(
            award=a1, request_number='DR-1', amount=Decimal('100000'),
            period_start=date.today() - timedelta(days=30),
            period_end=date.today(),
            status='paid', paid_at=timezone.now(),
            submitted_by=self.user,
        )
        # Pending drawdown should NOT be counted.
        DrawdownRequest.objects.create(
            award=a1, request_number='DR-2', amount=Decimal('50000'),
            period_start=date.today() - timedelta(days=15),
            period_end=date.today(),
            status='submitted',
            submitted_by=self.user,
        )
        active = Award.objects.filter(status__in=['active', 'executed'])
        out = _fund_source_breakdown(active)
        self.assertEqual(out['arpa']['drawn_cents'], 10000000)  # $100k * 100 = 10M cents

    def test_breakdown_separates_payment_and_refund_transactions(self):
        a1 = self._make_award(fund_source='iija', amount=500000, award_number='A1')
        Transaction.objects.create(
            award=a1, transaction_type='payment',
            amount=Decimal('80000'), transaction_date=date.today(),
        )
        Transaction.objects.create(
            award=a1, transaction_type='refund',
            amount=Decimal('5000'), transaction_date=date.today(),
        )
        active = Award.objects.filter(status__in=['active', 'executed'])
        out = _fund_source_breakdown(active)
        self.assertEqual(out['iija']['paid_cents'], 8000000)   # $80k * 100
        self.assertEqual(out['iija']['refunded_cents'], 500000)  # $5k * 100
