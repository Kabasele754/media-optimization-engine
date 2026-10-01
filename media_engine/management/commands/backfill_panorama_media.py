from django.core.management.base import BaseCommand
from media_engine.models import MediaAsset
from media_engine.queueing import enqueue_asset
from media_engine.processors.panorama.detect import detect_equirectangular


class Command(BaseCommand):
    help = 'Queue a panorama profile, including panoramas that already have an older profile.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--limit', type=int, default=0)
        parser.add_argument('--profile', default='panorama.multires', choices=['panorama.multires', 'panorama.marzipano', 'panorama.cube'])
        parser.add_argument('--force', action='store_true')

    def handle(self, *args, **options):
        queued = 0
        candidates = MediaAsset.objects.order_by('created_at')
        for asset in candidates.iterator():
            detection = detect_equirectangular(asset.width, asset.height, asset.metadata_json)
            if asset.media_kind != 'panorama' and not detection.is_panorama:
                continue
            self.stdout.write(f'{asset.id} {asset.width}x{asset.height} profile={options["profile"]}')
            if not options['dry_run']:
                if asset.media_kind != 'panorama':
                    asset.media_kind, asset.projection, asset.processor = 'panorama', detection.projection, 'panorama_360'
                    asset.save(update_fields=['media_kind', 'projection', 'processor', 'updated_at'])
                enqueue_asset(asset.id, profile=options['profile'], force=options['force'], backfill=True)
            queued += 1
            if options['limit'] and queued >= options['limit']:
                break
        self.stdout.write(self.style.SUCCESS(f'{"Would queue" if options["dry_run"] else "Queued"} panorama assets: {queued}'))
