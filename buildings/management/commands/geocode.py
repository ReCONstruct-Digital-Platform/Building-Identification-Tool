import traceback
import googlemaps

from django.utils import timezone
from buildings.models import Building
from config.settings import GOOGLE_API_KEY
  
from django.core.management.base import BaseCommand


def _parse_address_components(address_components):

    ret = {}

    for entry in address_components:
        types = entry['types']
        if 'street_number' in types:
            ret['street_number'] = entry['long_name']
        elif 'route' in types:
            ret['street_name'] = entry['long_name']
        elif 'locality' in types:
            ret['locality'] = entry['long_name']
        elif 'administrative_area_level_2' in types:
            ret['region'] = entry['long_name']
        elif 'administrative_area_level_1' in types:
            ret['province'] = entry['long_name']
            # province
        elif 'country' in types:
            ret['country'] = entry['long_name']
            # country
        elif 'postal_code' in types:
            ret['postal_code'] = entry['long_name']
        
    return ret

# This implements a django management command that can be invoked with
# python manage.py <comand>
class Command(BaseCommand):
    help = "Uses the Google Maps Geocoding API to get lat-lon from addresses"

    def add_arguments(self, parser):
        parser.add_argument('-n', '--num', default=0, type=int)

    def handle(self, *args, **options):
        gmaps = googlemaps.Client(key=GOOGLE_API_KEY)
        num_entries = options['num']

        print(f'Currently {len(Building.objects.all())} buildings in the database')

        with open('data/buildings.csv', 'r', encoding='utf-8') as infile:
            # Skip the header
            infile.readline()

            num_geocoded = 0
            for i, row in enumerate(infile):
                # Rate limit because we pay for Maps API usage
                if num_geocoded >= num_entries:
                    break

                data = row.rstrip().split(",")

                address = f'{data[0]}'.replace('-', ' ')
                print(address)
                lookup_results = Building.objects.filter(formatted_address__icontains=address)
                print(lookup_results)

                if len(lookup_results) > 0:
                    print(f'Already have geocoded row: {row}')
                    continue

                address = f'{data[0]} {data[3]} QC Canada'
                res = gmaps.geocode(address)
                # Only expecting a single returned address
                res = res[0]
                address_components = _parse_address_components(res['address_components'])

                try:
                    b = Building(
                        street_number = address_components['street_number'],
                        street_name = address_components['street_name'],
                        locality = address_components['locality'],
                        region = address_components['region'],
                        province = address_components['province'],
                        country = address_components['country'],
                        postal_code = address_components['postal_code'],
                        cubf = data[4], # category
                        formatted_address = res['formatted_address'],
                        lat = res['geometry']['location']['lat'],
                        lon = res['geometry']['location']['lng'],
                        date_added = timezone.now()
                    )
                    b.save()
                    num_geocoded += 1
                    print(f'Successfully geocoded Building {b}')

                except Exception as e:
                    traceback.print_exc()
                    print(f'Could not geocode row {row}.')

            self.stdout.write(self.style.SUCCESS(f'Successfully geocoded {num_geocoded} addresses'))
