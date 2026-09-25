from django.core.management.base import BaseCommand
from media_engine.models import MediaAsset
from media_engine.queueing import enqueue_asset
from media_engine.processors.panorama.detect import detect_equirectangular


class Command(BaseCommand):
    help = 'Detect existing 2:1 equirectangular assets and queue panorama multires processing.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--limit', type=int, default=0)

    def handle(self, *args, **options):
        changed = 0
        candidates = MediaAsset.objects.exclude(media_kind='panorama').order_by('created_at')
        if options['limit']:
            candidates = candidates[:options['limit']]
        for asset in candidates:
            detection = detect_equirectangular(asset.width, asset.height, asset.metadata_json)
            if not detection.is_panorama:
                continue
            self.stdout.write(f'{asset.id} {asset.width}x{asset.height}: {detection.reason}')
            if options['dry_run']:
                continue
            asset.media_kind = 'panorama'
            asset.projection = detection.projection
            asset.processor = 'panorama_360'
            asset.save(update_fields=['media_kind', 'projection', 'processor', 'updated_at'])
            enqueue_asset(asset.id, profile='panorama.multires', force=False)
            changed += 1
        self.stdout.write(self.style.SUCCESS(f'Queued panorama assets: {changed}'))
