from buildings.models import Building
from django.db.models import Count
  
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Remove buildings with the same address from the database"

    def add_arguments(self, parser):
        parser.add_argument('-d', '--delete', action="store_true", default=False)

    def handle(self, *args, **options):
        # Groups by unique formatted address, counts the unique IDs for each. 
        dupes = Building.objects.values('formatted_address').annotate(Count('id')).order_by().filter(id__count__gt=1)
        num_deleted = 0
        total_duplicates = 0

        for dup in dupes:
            # Return all duplicates except the first one (ordered by ID)
            duplicated_buildings = Building.objects.filter(formatted_address__exact=dup['formatted_address']).order_by('id')[1:]
            num_duplicates = len(duplicated_buildings)
            total_duplicates += num_duplicates

            if options['delete']:
                duplicated_buildings.delete()
                num_deleted += num_duplicates
            else:
                duplicate_ids = duplicated_buildings.values('id')
                self.stdout.write(f"Building at \'{dup['formatted_address']}\' has {num_duplicates} duplicates:\n\t{duplicate_ids}")
        
        if options['delete']:
            self.stdout.write(self.style.SUCCESS(f'Deleted {num_deleted} duplicated buildings!'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Identified {total_duplicates} duplicated buildings.'))
            if total_duplicates > 0:
                self.stdout.write('Re-run with \'-d/--delete\' option to delete them')
