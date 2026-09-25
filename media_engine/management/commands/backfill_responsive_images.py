from django.core.management.base import BaseCommand
from media_engine.models import MediaAsset
from media_engine.tasks import generate_asset_variants
from media_engine.queueing import enqueue_asset


class Command(BaseCommand):
    help = 'Generate missing responsive variants for existing MediaAsset rows.'

    def add_arguments(self, parser):
        parser.add_argument('--profile', default='default')
        parser.add_argument('--force', action='store_true')
        parser.add_argument('--sync', action='store_true')
        parser.add_argument('--limit', type=int)

    def handle(self, *args, **options):
        qs = MediaAsset.objects.order_by('created_at')
        if options['limit']:
            qs = qs[:options['limit']]
        count = 0
        for asset in qs.iterator():
            if options['sync']:
                generate_asset_variants.apply(args=[str(asset.id), options['profile'], options['force']]).get()
            else:
                enqueue_asset(asset.id, profile=options['profile'], force=options['force'], backfill=True)
            count += 1
        self.stdout.write(self.style.SUCCESS(f'Queued {count} assets.'))
