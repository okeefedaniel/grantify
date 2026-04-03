from keel.core.workflow import Transition, WorkflowEngine

AWARD_WORKFLOW = WorkflowEngine(transitions=[
    Transition(
        'draft', 'pending_approval',
        roles=['agency_staff'],
        label='Submit for Approval',
    ),
    Transition(
        'pending_approval', 'approved',
        roles=['grant_manager'],
        label='Approve Award',
    ),
    Transition(
        'approved', 'executed',
        roles=['grant_manager'],
        label='Execute Award',
    ),
    Transition(
        'executed', 'active',
        roles=['agency_staff'],
        label='Activate',
    ),
    Transition(
        'active', 'on_hold',
        roles=['grant_manager'],
        label='Place on Hold',
        require_comment=True,
    ),
    Transition(
        'on_hold', 'active',
        roles=['grant_manager'],
        label='Resume',
    ),
    Transition(
        'active', 'completed',
        roles=['grant_manager'],
        label='Complete',
    ),
    Transition(
        'active', 'terminated',
        roles=['grant_manager'],
        label='Terminate',
        require_comment=True,
    ),
    Transition(
        'pending_approval', 'cancelled',
        roles=['grant_manager'],
        label='Cancel',
    ),
    Transition(
        'draft', 'cancelled',
        roles=['agency_staff'],
        label='Cancel',
    ),
])
