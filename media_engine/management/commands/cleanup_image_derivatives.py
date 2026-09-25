from datetime import timedelta
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.utils import timezone
from media_engine.models import MediaVariant


class Command(BaseCommand):
    help = 'Delete old derivative versions after a retention period.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30)
        parser.add_argument('--confirm', action='store_true')

    def handle(self, *args, **options):
        version = getattr(settings, 'MEDIA_ENGINE_PIPELINE_VERSION', 1)
        threshold = timezone.now() - timedelta(days=options['days'])
        qs = MediaVariant.objects.filter(processor_version__lt=version, updated_at__lt=threshold)
        self.stdout.write(f'Candidates: {qs.count()}')
        if not options['confirm']:
            self.stdout.write('Dry run. Re-run with --confirm to delete.')
            return
        removed = 0
        for variant in qs.iterator():
            if variant.file and default_storage.exists(variant.file.name):
                default_storage.delete(variant.file.name)
            variant.delete()
            removed += 1
        self.stdout.write(self.style.SUCCESS(f'Deleted {removed} old variants.'))
