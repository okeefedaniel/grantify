from keel.core.workflow import Transition, WorkflowEngine

REPORT_WORKFLOW = WorkflowEngine(transitions=[
    Transition(
        'draft', 'submitted',
        roles=['any'],
        label='Submit Report',
    ),
    Transition(
        'submitted', 'under_review',
        roles=['agency_staff'],
        label='Begin Review',
    ),
    Transition(
        'submitted', 'approved',
        roles=['agency_staff'],
        label='Approve',
    ),
    Transition(
        'under_review', 'approved',
        roles=['agency_staff'],
        label='Approve',
    ),
    Transition(
        'submitted', 'revision_requested',
        roles=['agency_staff'],
        label='Request Revision',
        require_comment=True,
    ),
    Transition(
        'under_review', 'revision_requested',
        roles=['agency_staff'],
        label='Request Revision',
        require_comment=True,
    ),
    Transition(
        'revision_requested', 'submitted',
        roles=['any'],
        label='Resubmit',
    ),
    Transition(
        'submitted', 'rejected',
        roles=['grant_manager'],
        label='Reject',
        require_comment=True,
    ),
])
