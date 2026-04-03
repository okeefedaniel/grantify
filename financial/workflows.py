from keel.core.workflow import Transition, WorkflowEngine

DRAWDOWN_WORKFLOW = WorkflowEngine(transitions=[
    Transition(
        'draft', 'submitted',
        roles=['any'],
        label='Submit Request',
    ),
    Transition(
        'submitted', 'under_review',
        roles=['agency_staff'],
        label='Begin Review',
    ),
    Transition(
        'submitted', 'approved',
        roles=['fiscal_officer', 'agency_admin', 'system_admin'],
        label='Approve',
    ),
    Transition(
        'under_review', 'approved',
        roles=['fiscal_officer', 'agency_admin', 'system_admin'],
        label='Approve',
    ),
    Transition(
        'approved', 'paid',
        roles=['fiscal_officer', 'agency_admin', 'system_admin'],
        label='Mark Paid',
    ),
    Transition(
        'submitted', 'denied',
        roles=['fiscal_officer', 'agency_admin', 'system_admin'],
        label='Deny',
        require_comment=True,
    ),
    Transition(
        'submitted', 'returned',
        roles=['fiscal_officer', 'agency_admin', 'system_admin'],
        label='Return for Revision',
    ),
    Transition(
        'returned', 'submitted',
        roles=['any'],
        label='Resubmit',
    ),
])
