from keel.core.workflow import Transition, WorkflowEngine

CLOSEOUT_WORKFLOW = WorkflowEngine(transitions=[
    Transition(
        'not_started', 'in_progress',
        roles=['agency_staff'],
        label='Begin Closeout',
    ),
    Transition(
        'in_progress', 'pending_review',
        roles=['agency_staff'],
        label='Submit for Review',
    ),
    Transition(
        'pending_review', 'completed',
        roles=['grant_manager'],
        label='Complete Closeout',
    ),
    Transition(
        'pending_review', 'in_progress',
        roles=['grant_manager'],
        label='Return to In Progress',
        require_comment=True,
    ),
    Transition(
        'completed', 'reopened',
        roles=['grant_manager'],
        label='Reopen',
        require_comment=True,
    ),
    Transition(
        'reopened', 'in_progress',
        roles=['agency_staff'],
        label='Resume',
    ),
])
