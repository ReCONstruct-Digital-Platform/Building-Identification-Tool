import math
import os
import shutil
import IPython
import traceback
import psycopg2
import shapefile
import subprocess
import psycopg2.extras

from tqdm import tqdm
from pathlib import Path
from datetime import datetime
from django.db.models import Q
from django.db import connection
from buildings.models import EvalUnit
from buildings.utils.utility import download_file
from django.core.management.base import BaseCommand
from config.settings import BASE_DIR

DEFAULT_OUT = BASE_DIR / 'data'

EVALUNIT_TABLE = EvalUnit.objects.model._meta.db_table

DB_NAME = connection.settings_dict['NAME']
DB_HOST = connection.settings_dict['HOST']
DB_PORT = connection.settings_dict['PORT']
DB_USER = connection.settings_dict['USER']
DB_PW = connection.settings_dict['PASSWORD']
DB_CONN_STR = f"postgresql://{DB_USER}:{DB_PW}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# We create this table here, it's not associated with a model
LOTS_TABLE = 'lots'

class Command(BaseCommand):
    help = "Process the roll data and fill the database."

    def add_arguments(self, parser):
        parser.add_argument('-o', '--output-folder', 
                            type=Path, 
                            default=DEFAULT_OUT,
                            help='Path to folder containing the roll data, or where it will be downloaded.') 
        
        parser.add_argument('-d', '--download-data', 
                            action="store_true", 
                            default=False,
                            help="Download the data (~2GB). Automatically done if data can't be found.")
        
        parser.add_argument('-dd', '--delete-data', 
                            action="store_true", 
                            default=False,
                            help="Delete the data after processing (~2GB)")
        
        parser.add_argument('-t', '--test', 
                            action='store_true', 
                            default=False,
                            help="Run in testing mode (won't delete units without coords after)")
        

    def handle(self, *args, **options):

        data_folder: Path = options['output_folder']

        roll_shp_folder = data_folder / Path('roll_shp')
        roll_shp_folder.mkdir(exist_ok=True, parents=True)
        
        download_data = options['download_data']
        delete_data = options['delete_data']
        test = options['test']

        t0 = datetime.now()

        # Search the data directory for the shapefile
        if not list(roll_shp_folder.glob('**/rol_unite_p.shp')) or download_data:
            download_file("https://donneesouvertes.affmunqc.net/role/ROLE2022_SHP.zip", roll_shp_folder, unzip=True)
            self.stdout.write(self.style.SUCCESS('Roll points shapefile downloaded successfully'))

        shp_file = next(roll_shp_folder.glob('**/rol_unite_p.shp'))

        try:
            parse_shapefile(shp_file, test=test)
            self.stdout.write(
                self.style.SUCCESS(f'Finished parsing shapefile in {datetime.now() - t0} s')
            )
            if not test:
                count = cleanup_entries_without_coords()
                self.stdout.write(self.style.SUCCESS(f'Cleaned up {count} entries without coordinates'))
        except KeyboardInterrupt:
            self.stdout.write(self.style.ERROR('Interrupt received. Exiting.'))
            exit()
        finally:
            if delete_data:
                shutil.rmtree(data_folder)
                self.stdout.write(self.style.SUCCESS('Removed the downloaded data'))


def parse_shapefile(shp_file, test=False):

    # This curosr will handle commiting transactions
    with shapefile.Reader(shp_file) as shp, connection.cursor() as cursor:
        
        if test:
            num_units = 10_000 
        else:
            num_units = len(shp) 

        print(f'Shapefile contains {num_units} units')

        for i in tqdm(range(num_units), desc="Processing"):
            # The ID field is globally unique for evaluation units
            id = shp.record(i)[0]

            # We don't need to transform the coordinates, the point  
            # has lat/lng in NAD83 which is compatbile with WSG84.
            # In QGIS, changing the CRS from NAD83 to WDG84 performs the EPSG-1188 
            # transformation, which we see here https://epsg.io/1188 is a noop.
            lng, lat = shp.shape(i).points[0]
            cursor.execute(f"""
                UPDATE {EVALUNIT_TABLE} 
                SET
                    lng = %s,
                    lat = %s,
                    point = ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                    WHERE id = %s
            """, [lng, lat, lng, lat, id])


def cleanup_entries_without_coords():
    """
    Delete all entries for which we do not have coordinates
    """
    count = EvalUnit.objects.filter(Q(lat=None) | Q(lng=None)).count()
    EvalUnit.objects.filter(Q(lat=None) | Q(lng=None)).delete()
    assert EvalUnit.objects.filter(Q(lat=None) | Q(lng=None)).count() == 0
    return count

