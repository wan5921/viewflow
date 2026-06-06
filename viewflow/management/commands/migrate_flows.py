from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from viewflow.workflow.fields import import_flow_by_ref, get_flow_ref


class Command(BaseCommand):
    help = "Migrate flow processes and tasks from an old flow version to a new one"

    def add_arguments(self, parser):
        parser.add_argument(
            "source_flow",
            type=str,
            help="Source flow label, e.g. app_label/flows.MyFlow",
        )
        parser.add_argument(
            "target_flow",
            type=str,
            help="Target flow label, e.g. app_label/flows.MyFlowV2",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            help="Show what would be migrated without making changes",
        )

    def handle(self, **options):
        source_flow = import_flow_by_ref(options["source_flow"])
        target_flow = import_flow_by_ref(options["target_flow"])
        dry_run = options.get("dry_run", False)

        if source_flow is None:
            raise CommandError(
                "Source flow not found: {}".format(options["source_flow"])
            )
        if target_flow is None:
            raise CommandError(
                "Target flow not found: {}".format(options["target_flow"])
            )

        source_ref = get_flow_ref(source_flow)
        target_ref = get_flow_ref(target_flow)

        process_model = source_flow.process_class
        task_model = source_flow.task_class

        processes = process_model._default_manager.filter(flow_class=source_ref)
        process_count = processes.count()

        self.stdout.write(
            "Migrating {} process(es) from {} (v{}) to {} (v{})".format(
                process_count,
                source_flow.process_title,
                source_flow.version,
                target_flow.process_title,
                target_flow.version,
            )
        )

        if dry_run:
            self.stdout.write("DRY RUN - no changes will be made")
            for process in processes:
                self.stdout.write(
                    "  Would migrate Process #{} (status: {})".format(
                        process.pk, process.status
                    )
                )
            return

        with transaction.atomic():
            migrated_process = 0
            migrated_task = 0

            for process in processes:
                task_count = task_model._default_manager.filter(
                    process=process
                ).count()

                task_model._default_manager.filter(process=process).update(
                    flow_task_type="",
                )
                migrated_task += task_count

                process.flow_class = target_ref
                process.version = target_flow.version
                process.save(update_fields=["flow_class", "version"])
                migrated_process += 1

            self.stdout.write(
                self.style.SUCCESS(
                    "Migrated {} process(es) and {} task(s)".format(
                        migrated_process, migrated_task
                    )
                )
            )