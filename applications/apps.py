from django.apps import AppConfig


class ApplicationsConfig(AppConfig):
    name = 'applications'

    def ready(self):
        # Register keel.activity Track A promotion rules.
        # Phase 1A Week 5 / Phase 1C — Harbor is the second non-pilot peer.
        try:
            from applications.activity_promotions import register_all
            register_all()
        except ImportError:
            pass
