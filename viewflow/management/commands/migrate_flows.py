from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from viewflow.workflow.fields import import_flow_by_ref
from viewflow.workflow.models import Process


class Command(BaseCommand):
    help = "Migrate processes from old flow version to new version"

    def add_arguments(self, parser):
        parser.add_argument(
            "flow_label",
            type=str,
            help="Flow label, i.e. app_label/flows.MyFlow",
        )
        parser.add_argument(
            "--from-version",
            type=int,
            default=1,
            help="Source version to migrate from (default: 1)",
        )
        parser.add_argument(
            "--to-version",
            type=int,
            required=True,
            help="Target version to migrate to",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be migrated without actually doing it",
        )
        parser.add_argument(
            "--process-pks",
            type=str,
            help="Comma-separated list of specific process PKs to migrate",
        )

    def handle(self, **options):
        flow_class = import_flow_by_ref(options["flow_label"])
        if flow_class is None:
            raise CommandError(f"Flow not found: {options['flow_label']}")

        from_version = options["from_version"]
        to_version = options["to_version"]
        dry_run = options["dry_run"]
        process_pks = options.get("process_pks")

        if from_version >= to_version:
            raise CommandError("from-version must be less than to-version")

        queryset = Process.objects.filter(
            flow_class=flow_class,
            version=from_version,
        )

        if process_pks:
            pks = [int(pk.strip()) for pk in process_pks.split(",")]
            queryset = queryset.filter(pk__in=pks)

        count = queryset.count()

        if count == 0:
            self.stdout.write(
                self.style.WARNING(
                    f"No processes found for {flow_class.process_title} "
                    f"version {from_version}"
                )
            )
            return

        self.stdout.write(
            f"Found {count} processes to migrate from version "
            f"{from_version} to {to_version}"
        )

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes will be made"))
            for process in queryset[:10]:
                self.stdout.write(f"  Would migrate Process #{process.pk}")
            if count > 10:
                self.stdout.write(f"  ... and {count - 10} more")
            return

        with transaction.atomic():
            updated = queryset.update(version=to_version)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully migrated {updated} processes to version {to_version}"
            )
        )
