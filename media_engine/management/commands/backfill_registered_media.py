from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from media_engine.integration import ingest_model_field
from media_engine.registry import entries


class Command(BaseCommand):
    help = 'Ingest image fields declared through register_model_image().'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int)
        parser.add_argument(
            '--fail-fast',
            action='store_true',
            help='Stop immediately on the first invalid/unreadable image.',
        )

    def handle(self, *args, **options):
        processed = 0
        skipped = 0
        failed = 0
        failures = []

        for entry in entries():
            qs = entry.model._default_manager.all()
            if options['limit']:
                qs = qs[:options['limit']]

            for obj in qs.iterator():
                try:
                    asset = ingest_model_field(
                        obj,
                        field_name=entry.field_name,
                        profile=entry.profile,
                        role=entry.role,
                    )
                    if asset is None:
                        skipped += 1
                    else:
                        processed += 1
                except ValidationError as exc:
                    failed += 1
                    message = (
                        f'{entry.model._meta.label}.{entry.field_name} '
                        f'pk={obj.pk}: {exc}'
                    )
                    failures.append(message)
                    self.stderr.write(self.style.WARNING(f'SKIP {message}'))
                    if options['fail_fast']:
                        raise
                except (FileNotFoundError, OSError, ValueError) as exc:
                    failed += 1
                    message = (
                        f'{entry.model._meta.label}.{entry.field_name} '
                        f'pk={obj.pk}: {exc}'
                    )
                    failures.append(message)
                    self.stderr.write(self.style.WARNING(f'SKIP {message}'))
                    if options['fail_fast']:
                        raise

        summary = (
            f'Processed {processed} registered model images; '
            f'skipped {skipped}; failures {failed}.'
        )
        if failed:
            self.stdout.write(self.style.WARNING(summary))
            self.stdout.write('Last failures:')
            for message in failures[-20:]:
                self.stdout.write(f'  - {message}')
        else:
            self.stdout.write(self.style.SUCCESS(summary))
