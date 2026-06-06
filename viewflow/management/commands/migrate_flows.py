from django.core.management.base import BaseCommand
from viewflow.workflow.models import Process

class Command(BaseCommand):
    help = 'Migrate old flow tasks to a new version'

    def add_arguments(self, parser):
        parser.add_argument('flow_class', type=str, help='Flow class reference (e.g. "app_label/flows.MyFlow")')
        parser.add_argument('new_version', type=int, help='New version to migrate to')

    def handle(self, *args, **options):
        flow_class = options['flow_class']
        new_version = options['new_version']
        
        processes = Process.objects.filter(flow_class=flow_class, version__lt=new_version)
        count = processes.update(version=new_version)
        self.stdout.write(self.style.SUCCESS(f'Successfully migrated {count} processes to version {new_version}'))
