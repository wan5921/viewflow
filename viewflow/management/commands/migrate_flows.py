from django.core.management.base import BaseCommand
from django.db import transaction
from viewflow.workflow import Flow
from viewflow.workflow.models import Process, Task


class Command(BaseCommand):
    help = "Migrate old process and task instances to new flow versions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--to-version",
            type=int,
            help="Target version to migrate to (defaults to latest available)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        to_version = options["to_version"]

        self.stdout.write("Starting flow migration...")

        # Find all Flow subclasses
        flow_classes = self._find_flow_classes()

        for flow_class in flow_classes:
            self.stdout.write(f"\nProcessing flow: {flow_class.__name__}")

            # Get latest version for this flow
            latest_version = flow_class.version
            if to_version and to_version > latest_version:
                self.stdout.write(
                    self.style.WARNING(
                        f"Requested version {to_version} is higher than latest {latest_version} for {flow_class.__name__}"
                    )
                )
                continue

            target_version = to_version if to_version else latest_version

            # Find all processes for this flow with version < target_version
            processes = Process.objects.filter(
                flow_class=flow_class, version__lt=target_version
            )

            self.stdout.write(
                f"Found {processes.count()} processes to migrate to version {target_version}"
            )

            if not processes.exists():
                continue

            if not dry_run:
                with transaction.atomic():
                    for process in processes:
                        # Update process version
                        process.version = target_version
                        process.save()

                        # Update all tasks for this process
                        tasks = Task.objects.filter(process=process)
                        for task in tasks:
                            # Re-save task to update flow_task reference with new version
                            task.save()

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Successfully migrated {processes.count()} processes"
                        )
                    )
            else:
                self.stdout.write(
                    self.style.WARNING("Dry run: no changes made")
                )

        self.stdout.write(self.style.SUCCESS("\nMigration complete!"))

    def _find_flow_classes(self):
        """Find all subclasses of Flow in all installed apps."""
        from django.apps import apps
        from importlib import import_module

        flow_classes = []

        for app_config in apps.get_app_configs():
            try:
                # Try to import flows module
                flows_module = import_module(f"{app_config.name}.flows")
                for name in dir(flows_module):
                    obj = getattr(flows_module, name)
                    try:
                        if issubclass(obj, Flow) and obj is not Flow:
                            flow_classes.append(obj)
                    except TypeError:
                        continue
            except ImportError:
                continue

            # Also check models
            try:
                models_module = import_module(f"{app_config.name}.models")
                for name in dir(models_module):
                    obj = getattr(models_module, name)
                    try:
                        if issubclass(obj, Flow) and obj is not Flow:
                            flow_classes.append(obj)
                    except TypeError:
                        continue
            except ImportError:
                continue

        return flow_classes
