from django.apps import AppConfig


class AwardsConfig(AppConfig):
    name = 'awards'

    def ready(self):
        # Wire the packet_approved receiver: on Manifest roundtrip
        # completion, file the signed PDF on the award + transition
        # Award.status to EXECUTED.
        from . import signals  # noqa: F401
