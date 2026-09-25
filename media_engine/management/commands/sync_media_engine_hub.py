import json
from django.core.management.base import BaseCommand, CommandError
from media_engine.control_plane import sync_from_control_plane


class Command(BaseCommand):
    help = 'Synchronize optional Ziarama Hub configuration without making runtime depend on the hub.'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true')

    def handle(self, *args, **options):
        result = sync_from_control_plane(force=options['force'])
        self.stdout.write(json.dumps(result, indent=2, sort_keys=True))
        if result.get('state') == 'degraded':
            self.stderr.write(self.style.WARNING('Hub unavailable; engine continues with last-known-good/local config.'))
