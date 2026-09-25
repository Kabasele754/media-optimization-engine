from django.core.management.base import BaseCommand

from media_engine.doctor import format_report, run_diagnostics


class Command(BaseCommand):
    help = "Diagnose Media Optimization Engine integration, migrations, storage and codecs."

    def handle(self, *args, **options):
        checks = run_diagnostics()
        report = format_report(checks)
        self.stdout.write(report)
        errors = [c for c in checks if not c.ok and c.level != "WARN"]
        if errors:
            raise SystemExit(1)
