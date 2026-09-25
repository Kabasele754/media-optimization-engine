from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Sum
from media_engine.models import MediaAsset, MediaVariant
from media_engine.profiles import get_profile, requested_widths, all_formats


class Command(BaseCommand):
    help = 'Audit media assets and responsive variants.'

    def add_arguments(self, parser):
        parser.add_argument('--profile', default='default')
        parser.add_argument('--fail-on-incomplete', action='store_true')

    def handle(self, *args, **options):
        profile_name = options['profile']
        profile = get_profile(profile_name)
        version = getattr(settings, 'MEDIA_ENGINE_PIPELINE_VERSION', 1)
        total = MediaAsset.objects.count()
        ready_assets = 0
        incomplete = 0
        expected_total = 0
        for asset in MediaAsset.objects.all().iterator():
            expected = len(requested_widths(profile, asset.width)) * len(all_formats(profile))
            expected_total += expected
            ready = MediaVariant.objects.filter(
                asset=asset,
                profile=profile_name,
                processor_version=version,
                status=MediaVariant.Status.READY,
            ).count()
            if ready >= expected:
                ready_assets += 1
            else:
                incomplete += 1

        original_bytes = MediaAsset.objects.aggregate(v=Sum('original_size'))['v'] or 0
        derivative_bytes = MediaVariant.objects.filter(status=MediaVariant.Status.READY).aggregate(v=Sum('file_size'))['v'] or 0
        avif = MediaVariant.objects.filter(format='avif', status=MediaVariant.Status.READY).count()
        webp = MediaVariant.objects.filter(format='webp', status=MediaVariant.Status.READY).count()
        failed = MediaVariant.objects.filter(status=MediaVariant.Status.FAILED).count()

        self.stdout.write(f'Pipeline version: {version}')
        self.stdout.write(f'Original images: {total}')
        self.stdout.write(f'Ready responsive images: {ready_assets}')
        self.stdout.write(f'Missing/incomplete: {incomplete}')
        self.stdout.write(f'Expected variants: {expected_total}')
        self.stdout.write(f'AVIF variants: {avif}')
        self.stdout.write(f'WebP variants: {webp}')
        self.stdout.write(f'Failed variants: {failed}')
        self.stdout.write(f'Original storage: {original_bytes / (1024 * 1024):.2f} MB')
        self.stdout.write(f'Responsive derivatives: {derivative_bytes / (1024 * 1024):.2f} MB')
        if options['fail_on_incomplete'] and incomplete:
            raise SystemExit(2)
