"""Read-only descriptor benchmark. Does not generate or download panoramas."""
import json
import statistics
import time
from django.core.management.base import BaseCommand, CommandError
from media_engine.models import MediaAsset
from media_engine.manifest import build_manifest
from media_engine.adapters.marzipano import to_marzipano


class Command(BaseCommand):
    help = 'Measure panorama manifest construction and JSON size (not browser/network/GPU speed).'

    def add_arguments(self, parser):
        parser.add_argument('--asset-id', required=True)
        parser.add_argument('--profile', default='panorama.marzipano')
        parser.add_argument('--runs', type=int, default=10)

    def handle(self, *args, **options):
        if not 1 <= options['runs'] <= 100:
            raise CommandError('--runs must be between 1 and 100')
        try:
            asset = MediaAsset.objects.get(pk=options['asset_id'], media_kind='panorama')
        except (MediaAsset.DoesNotExist, ValueError):
            raise CommandError('Panorama asset not found')
        report = {'asset_id': str(asset.pk), 'runs': options['runs'], 'results': {}}
        for compact in (False, True):
            durations = []
            for _ in range(options['runs']):
                start = time.perf_counter()
                value = to_marzipano(build_manifest(asset, profile=options['profile'], compact=compact))
                encoded = json.dumps(value, separators=(',', ':')).encode()
                durations.append((time.perf_counter() - start) * 1000)
            ordered = sorted(durations)
            report['results']['compact' if compact else 'explicit'] = {
                'first_ms': durations[0], 'median_ms': statistics.median(durations),
                'p95_ms': ordered[min(len(ordered) - 1, int(len(ordered) * .95))],
                'json_bytes': len(encoded), 'actual_template': bool(value.get('urlTemplate')),
                'ready': value.get('ready', False), 'revision': value.get('revision', '')}
        self.stdout.write(json.dumps(report, indent=2))
