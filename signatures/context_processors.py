"""
Template context processor for the signatures app.

Provides ``sig_base_template`` and ``sig_dashboard_url`` so templates can
extend the correct base template in both Harbor and standalone mode.
"""

from .compat import is_harbor


def manifest_context(request):
    if is_harbor():
        return {
            'sig_base_template': 'base.html',
            'sig_dashboard_url': 'dashboard',
            'manifest_brand': 'Harbor',
        }
    return {
        'sig_base_template': 'manifest/base.html',
        'sig_dashboard_url': 'signatures:packet-list',
        'manifest_brand': 'Manifest',
    }
