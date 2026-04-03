from keel.core.workflow import Transition, WorkflowEngine

APPLICATION_WORKFLOW = WorkflowEngine(
    transitions=[
        Transition(
            'draft', 'submitted',
            roles=['applicant', 'agency_staff'],
            label='Submit Application',
        ),
        Transition(
            'submitted', 'under_review',
            roles=['agency_staff'],
            label='Begin Review',
        ),
        Transition(
            'under_review', 'approved',
            roles=['grant_manager'],
            label='Approve',
        ),
        Transition(
            'under_review', 'denied',
            roles=['grant_manager'],
            label='Deny',
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
            roles=['applicant'],
            label='Resubmit',
        ),
        Transition(
            'submitted', 'withdrawn',
            roles=['applicant'],
            label='Withdraw',
        ),
        Transition(
            'draft', 'withdrawn',
            roles=['applicant'],
            label='Withdraw',
        ),
    ],
    history_model='applications.ApplicationStatusHistory',
    history_fk_field='application',
)
