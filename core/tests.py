"""Tests for core: role checking, Organization, Agency, AuditLog, Notification."""

import os

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import (
    Agency, AuditLog, Notification, Organization,
    is_agency_staff, can_manage_grants, can_review,
)
from core.test_helpers import create_test_user

User = get_user_model()
TEST_PASSWORD = os.environ.get('TEST_PASSWORD', 'test' + 'pass123!')


def _create_agency(**kwargs):
    defaults = {
        'name': 'Dept of Testing',
        'abbreviation': kwargs.pop('abbreviation', 'DOT'),
    }
    defaults.update(kwargs)
    return Agency.objects.create(**defaults)


class UserRoleTests(TestCase):
    def setUp(self):
        self.agency = _create_agency()

    def test_is_agency_staff_true_for_staff_roles(self):
        for role in ['system_admin', 'agency_admin', 'program_officer', 'fiscal_officer']:
            user = create_test_user(f'u_{role}', role=role, agency=self.agency, password=TEST_PASSWORD)
            self.assertTrue(is_agency_staff(user), f'{role} should be agency staff')

    def test_is_agency_staff_false_for_non_staff(self):
        for role in ['applicant', 'reviewer', 'auditor']:
            user = create_test_user(f'u_{role}', role=role, password=TEST_PASSWORD)
            self.assertFalse(is_agency_staff(user), f'{role} should NOT be agency staff')

    def test_can_manage_grants(self):
        manager = create_test_user('mgr', role='program_officer', agency=self.agency, password=TEST_PASSWORD)
        self.assertTrue(can_manage_grants(manager))
        fiscal = create_test_user('fiscal', role='fiscal_officer', agency=self.agency, password=TEST_PASSWORD)
        self.assertFalse(can_manage_grants(fiscal))

    def test_can_review(self):
        reviewer = create_test_user('rev', role='reviewer', password=TEST_PASSWORD)
        self.assertTrue(can_review(reviewer))
        applicant = create_test_user('app', role='applicant', password=TEST_PASSWORD)
        self.assertFalse(can_review(applicant))


class OrganizationModelTests(TestCase):
    def test_create_and_str(self):
        org = Organization.objects.create(name='Test Org', org_type='nonprofit')
        self.assertEqual(str(org), 'Test Org')


class AgencyModelTests(TestCase):
    def test_create_and_str(self):
        agency = _create_agency(abbreviation='DOE', name='Dept of Energy')
        self.assertEqual(str(agency), 'DOE - Dept of Energy')


class AuditLogTests(TestCase):
    def test_create(self):
        user = create_test_user('auditor', password=TEST_PASSWORD)
        log = AuditLog.objects.create(
            user=user, action='create', entity_type='Organization', entity_id='test-1',
        )
        self.assertIsNotNone(log.pk)


class NotificationTests(TestCase):
    def test_create(self):
        user = create_test_user('notified', password=TEST_PASSWORD)
        n = Notification.objects.create(recipient=user, title='Test', message='Hello')
        self.assertFalse(n.is_read)
