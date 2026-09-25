from django.core.management.base import BaseCommand
from media_engine.integration import ingest_model_field
from media_engine.registry import entries


class Command(BaseCommand):
    help = 'Ingest image fields declared through register_model_image().' 

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int)

    def handle(self, *args, **options):
        processed = 0
        for entry in entries():
            qs = entry.model._default_manager.all()
            if options['limit']:
                qs = qs[:options['limit']]
            for obj in qs.iterator():
                ingest_model_field(obj, field_name=entry.field_name, profile=entry.profile, role=entry.role)
                processed += 1
        self.stdout.write(self.style.SUCCESS(f'Processed {processed} registered model images.'))
