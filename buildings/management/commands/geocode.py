import traceback
import googlemaps
from pathlib import Path

from django.utils import timezone
from buildings.models import Building
from config.settings import GOOGLE_MAPS_API_KEY
  
from django.core.management.base import BaseCommand

from datetime import datetime

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
        elif 'administrative_area_level_3' in types:
            ret['admin_area_3'] = entry['long_name']
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
        parser.add_argument('-f', '--file', default="data/buildings.csv", type=str, help="CSV file of buildings to create.")

    def handle(self, *args, **options):
        gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
        num_entries = options['num']
        data_file = Path(options['file'])

        logdir = Path('log')
        logdir.mkdir(exist_ok=True)
        logfile = logdir / "geocode.log"

        num_buildings_in_db = len(Building.objects.all())

        print(f'{datetime.now()} Currently {num_buildings_in_db} buildings in the database')

        if not (data_file.exists() and data_file.is_file()):
            self.stderr.write(self.style.ERROR(f'Invalid data file given: {data_file}'))
            return
        
        # import code 
        # code.interact(local=locals())

        with open(data_file, 'r', encoding='utf-8') as infile, open(logfile, 'w', encoding='utf-8') as logfile:
            # Skip the header
            infile.readline()

            num_geocoded = 0
            for i, row in enumerate(infile):

                # Rate limit because we pay for Maps API usage
                if num_geocoded >= num_entries:
                    break

                data = row.rstrip().split(",")

                csv_address = f'{data[0]} {data[3]} QC Canada'

                serial_number = data[5].replace(' ', '').strip()

                # These fields can be '9999' indicating a null value
                lin_dim = float(data[6]) if data[6] != '9999.0' else None
                area = float(data[7]) if data[7] != '9999.0' else None
                max_num_floor = int(data[8]) if data[8] != '9999' else None
                construction_year = int(data[9]) if data[9] != '9999' else None
                year_real_esti = data[10] if data[10] != '9999' else None
                floor_area = float(data[11]) if data[11] != '9999.0' else None
                type_const = int(data[13]) if data[13] != '9999' else None
                num_dwell = int(data[14]) if data[14] != '9999' else None
                num_rental = int(data[15]) if data[15] != '9999' else None
                num_non_res = int(data[16]) if data[16] != '9999' else None
                value_prop = int(data[17]) if data[17] != '9999' else None

                # import code 
                # code.interact(local=locals())

                # Often the original address is not similar enough to detect duplicates before geocoding
                if Building.objects.filter(serial_number=serial_number).exists():
                    print(f'{datetime.now()} Already have geocoded row: {row.rstrip()}')
                    continue

                res = gmaps.geocode(csv_address)
                # Only expecting a single returned address
                res = res[0]
                address_components = _parse_address_components(res['address_components'])

                try:
                    locality = None
                    if 'locality' in address_components:
                        locality = address_components['locality']
                    elif 'admin_area_3' in address_components:
                        locality = address_components['admin_area_3']
                    
                    b = Building(
                        street_number = address_components['street_number'],
                        street_name = address_components['street_name'],
                        locality = locality,
                        region = address_components['region'],
                        province = address_components['province'],
                        country = address_components['country'],
                        postal_code = address_components['postal_code'],
                        cubf = data[4], # category
                        formatted_address = res['formatted_address'],
                        lat = res['geometry']['location']['lat'],
                        lon = res['geometry']['location']['lng'],
                        serial_number = serial_number,
                        lin_dim = lin_dim,
                        area = area,
                        max_num_floor = max_num_floor,
                        construction_year = construction_year,
                        year_real_esti = year_real_esti,
                        floor_area = floor_area,
                        type_const = type_const,
                        num_dwell = num_dwell,
                        num_rental = num_rental,
                        num_non_res = num_non_res,
                        value_prop = value_prop,
                        csv_address = csv_address,
                        place_id = res['place_id'],
                        date_added = timezone.now(),
                    )
                    b.save()
                    num_geocoded += 1
                    self.stdout.write(self.style.SUCCESS(f'{datetime.now()} Successfully geocoded Building {b}'))
                    logfile.write(f'{datetime.now()} Successfully geocoded Building {b}\n')

                except:
                    stacktrace = traceback.format_exc()

                    self.stdout.write(self.style.WARNING(f'Could not geocode row:\n\t{row}.'))
                    self.stdout.write(self.style.WARNING(stacktrace))

                    logfile.write(f'{datetime.now()} Could not geocode row:\n\t{row.rstrip()}.\n')
                    logfile.write(stacktrace)

            self.stdout.write(self.style.SUCCESS(f'{datetime.now()} Successfully geocoded {num_geocoded} addresses'))
