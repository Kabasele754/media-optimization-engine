import json
from django.core.management.base import BaseCommand, CommandError
from media_engine.control_plane import rollback_to_previous


class Command(BaseCommand):
    help = 'Rollback to the previous last-known-good control-plane profile configuration.'

    def handle(self, *args, **options):
        try:
            result = rollback_to_previous()
        except RuntimeError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(result, indent=2, sort_keys=True))
