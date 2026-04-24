"""
Signature workflow orchestration — thin re-export of the shared
``keel.signatures.services`` module.

Phase (b) of the extraction plan in
``keel/keel/signatures/__init__.py`` moved the byte-identical harbor +
manifest ``services.py`` bodies into keel. The bespoke models stay in
each product (phase e still deferred); the shared services.py resolves
them at runtime via ``apps.get_model('signatures', …)``.

The product-local compat.py stays product-local (phase c deferred)
because it embeds harbor-specific role enums and manifest-specific
SignatureRole model access that don't share cleanly. The keel-hosted
services.py imports compat from the absolute path ``signatures.compat``.
"""
from keel.signatures.services import *  # noqa: F401, F403
