import json
from django.core.management.base import BaseCommand, CommandError
from django.core.files.storage import default_storage
from media_engine.models import MediaAsset, PanoramaBuild
from media_engine.processors.panorama.manifest import panorama_manifest


class Command(BaseCommand):
    help = 'Read-only audit of published panorama completeness and optional storage checks.'

    def add_arguments(self, parser):
        parser.add_argument('--profile', default='panorama.multires')
        parser.add_argument('--limit', type=int, default=0)
        parser.add_argument('--check-files', action='store_true')
        parser.add_argument('--json', action='store_true')
        parser.add_argument('--fail-on-incomplete', action='store_true')

    def handle(self, *args, **options):
        assets = MediaAsset.objects.filter(media_kind='panorama').order_by('created_at')
        if options['limit']:
            assets = assets[:options['limit']]
        report = []
        for asset in assets:
            manifest = panorama_manifest(asset, options['profile'])
            missing = []
            active = PanoramaBuild.objects.filter(asset=asset, profile=options['profile'], is_active=True).first()
            if options['check_files']:
                names = [asset.panorama_preview.name] if asset.panorama_preview else []
                if active:
                    names = [active.preview.name] + [t['file'] for level in active.manifest.get('levels', [])
                        for tiles in level.get('formats', {}).values() for t in tiles]
                else:
                    names += list(asset.panorama_tiles.filter(build__isnull=True, profile=options['profile'],
                        processor_version=asset.processor_version, status='READY').values_list('file', flat=True))
                missing = [name for name in names if name and not default_storage.exists(name)]
            report.append({'asset_id': str(asset.pk), 'revision': manifest['revision'],
                'state': manifest['state'], 'levels': manifest['published_levels'],
                'complete': manifest['complete'] and not missing, 'missing_files': missing})
        if options['json']:
            self.stdout.write(json.dumps(report, indent=2))
        else:
            for row in report:
                self.stdout.write(f"{row['asset_id']} {row['state']} levels={row['levels']} complete={row['complete']} missing={len(row['missing_files'])}")
            self.stdout.write(f"Complete panoramas: {sum(row['complete'] for row in report)}/{len(report)}")
        if options['fail_on_incomplete'] and any(not row['complete'] for row in report):
            raise CommandError('Incomplete panoramas or missing published files')
