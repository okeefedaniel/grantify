from keel.core.workflow import Transition, WorkflowEngine

GRANT_PROGRAM_WORKFLOW = WorkflowEngine(transitions=[
    Transition(
        'draft', 'posted',
        roles=['grant_manager'],
        label='Post',
    ),
    Transition(
        'posted', 'accepting_applications',
        roles=['grant_manager'],
        label='Open Applications',
    ),
    Transition(
        'accepting_applications', 'under_review',
        roles=['grant_manager'],
        label='Close Applications & Review',
    ),
    Transition(
        'under_review', 'awards_pending',
        roles=['grant_manager'],
        label='Finalize Reviews',
    ),
    Transition(
        'awards_pending', 'closed',
        roles=['grant_manager'],
        label='Close Program',
    ),
    Transition(
        'posted', 'cancelled',
        roles=['grant_manager'],
        label='Cancel',
    ),
    Transition(
        'posted', 'draft',
        roles=['grant_manager'],
        label='Unpublish',
    ),
])
