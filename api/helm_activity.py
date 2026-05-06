"""Cross-product activity feed endpoint.

Wraps keel.feed.views.helm_activity_view (added in keel 0.28.7) which is
generic over any product's concrete Activity model. The factory resolves
KEEL_ACTIVITY_MODEL at request time and serves the most recent N rows.
Helm's aggregator polls this on the schedule defined by its fetch_feeds
job and renders one chronological wall in /dashboard/?tab=stream.

Wire shape and query params: see helm_activity_view docstring.
"""
from keel.feed.views import helm_activity_view


harbor_helm_activity = helm_activity_view()
