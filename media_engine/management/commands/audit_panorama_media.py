from django.core.management.base import BaseCommand
from media_engine.models import MediaAsset, PanoramaTile


class Command(BaseCommand):
    help = 'Audit 360 panorama assets and multiresolution tile completeness.'

    def handle(self, *args, **options):
        assets = MediaAsset.objects.filter(media_kind='panorama')
        total = assets.count()
        ready = assets.filter(status='READY').count()
        failed = assets.filter(status='FAILED').count()
        tiles = PanoramaTile.objects.count()
        ready_tiles = PanoramaTile.objects.filter(status='READY').count()
        bytes_total = sum(PanoramaTile.objects.filter(status='READY').values_list('file_size', flat=True))
        self.stdout.write(f'Panorama assets: {total}')
        self.stdout.write(f'Ready panoramas: {ready}')
        self.stdout.write(f'Failed panoramas: {failed}')
        self.stdout.write(f'Tiles: {ready_tiles}/{tiles}')
        self.stdout.write(f'Tile storage: {bytes_total / (1024 * 1024):.2f} MB')
