from django.core.management.base import BaseCommand, CommandError
from django.db.models import Max

from viewflow.workflow.fields import import_flow_by_ref


class Command(BaseCommand):
    help = "Migrate active flow processes to a newer version"

    def add_arguments(self, parser):
        parser.add_argument(
            "flow_label",
            nargs=1,
            type=str,
            help="Flow label, i.e. app_label/flows.MyFlow",
        )
        parser.add_argument(
            "--from-version",
            type=int,
            required=True,
            dest="from_version",
            help="Current process version to migrate from",
        )
        parser.add_argument(
            "--to-version",
            type=int,
            dest="to_version",
            help="Target process version. Defaults to the next flow version.",
        )
        parser.add_argument(
            "--include-finished",
            action="store_true",
            dest="include_finished",
            help="Include finished processes in the migration",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            help="Show how many processes would be migrated without updating them",
        )

    def handle(self, *args, **options):
        flow_class = import_flow_by_ref(options["flow_label"][0])
        from_version = options["from_version"]
        target_version = options.get("to_version")

        if target_version is None:
            current_version = (
                flow_class.process_class._default_manager.filter(flow_class=flow_class)
                .aggregate(max_version=Max("version"))
                .get("max_version")
                or flow_class.version
            )
            target_version = flow_class(version=current_version + 1).version
        else:
            target_version = flow_class(version=target_version).version

        if from_version == target_version:
            raise CommandError("Source and target versions must be different")

        queryset = flow_class.process_class._default_manager.filter(
            flow_class=flow_class,
            version=from_version,
        )

        if not options["include_finished"]:
            queryset = queryset.filter(finished__isnull=True)

        total = queryset.count()

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING(
                    f"Would migrate {total} processes for {flow_class} from version {from_version} to {target_version}."
                )
            )
            return

        migrated = queryset.update(version=target_version)
        self.stdout.write(
            self.style.SUCCESS(
                f"Migrated {migrated} processes for {flow_class} from version {from_version} to {target_version}."
            )
        )
