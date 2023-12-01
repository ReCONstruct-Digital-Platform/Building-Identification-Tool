import os
import IPython
import traceback
import django
import psycopg2
import psycopg2.extras

from tqdm import tqdm
from pathlib import Path
from statistics import mean
from datetime import datetime
from collections import Counter
from multiprocessing import Pool
from django.db import connection
from psycopg2.extras import execute_values
from buildings.utils.utility import split_list_in_n, get_DB_conn

from config.settings import BASE_DIR
from buildings.models import EvalUnit
from django.core.management.base import BaseCommand

DEFAULT_OUT = BASE_DIR / 'data'

DB_NAME = connection.settings_dict['NAME']
DB_HOST = connection.settings_dict['HOST']
DB_PORT = connection.settings_dict['PORT']
DB_USER = connection.settings_dict['USER']
DB_PW = connection.settings_dict['PASSWORD']
DB_CONN_STR = f"postgresql://{DB_USER}:{DB_PW}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

EVALUNIT_TABLE = EvalUnit.objects.model._meta.db_table
# Table is created here, not linked to a model
MURB_DISAG_TABLE = 'murb_disag'


SQL_COPY_TEMPLATE = """(%(id)s, %(agg_id)s, %(lat)s, %(lng)s, %(point)s, %(lot_id)s, %(lot_geom)s, 
    %(year)s, %(muni)s, %(muni_code)s, %(arrond)s, %(address)s, %(num_adr_inf)s, %(num_adr_inf_2)s, 
    %(num_adr_sup)s, %(num_adr_sup_2)s, %(street_name)s, %(apt_num)s, %(apt_num_1)s, %(apt_num_2)s, 
    %(mat18)s, %(cubf)s, %(file_num)s, %(nghbr_unit)s, %(owner_date)s, %(owner_type)s, %(owner_status)s, 
    %(lot_lin_dim)s, %(lot_area)s, %(max_floors)s, %(const_yr)s, %(const_yr_real)s, %(floor_area)s, 
    %(phys_link)s, %(const_type)s, %(num_dwelling)s, %(num_rental)s, %(num_non_res)s, %(apprais_date)s, 
    %(lot_value)s, %(building_value)s, %(value)s, %(prev_value)s, %(date_added)s)"""

SQL_COPY_DUPLICATES_TO_OTHER_TABLE = f"""INSERT INTO {MURB_DISAG_TABLE}
    (id, agg_id, lat, lng, point, lot_id, lot_geom, year, muni, muni_code, arrond, address, num_adr_inf, 
    num_adr_inf_2, num_adr_sup, num_adr_sup_2, street_name, apt_num, apt_num_1, apt_num_2, mat18, cubf, 
    file_num, nghbr_unit, owner_date, owner_type, owner_status, lot_lin_dim, lot_area, max_floors, const_yr, 
    const_yr_real, floor_area, phys_link, const_type, num_dwelling, num_rental, num_non_res, apprais_date, 
    lot_value, building_value, value, prev_value, date_added) VALUES %s ON CONFLICT DO NOTHING"""

SQL_INSERT_AGGREGATED_MURB = f"""INSERT INTO {EVALUNIT_TABLE}
        (id, lat, lng, point, lot_id, lot_geom, year, muni, muni_code, arrond, address, street_name, 
        mat18, cubf, nghbr_unit, owner_date, owner_type, owner_status, lot_lin_dim, lot_area, max_floors, 
        const_yr, const_yr_real, floor_area, phys_link, const_type, num_dwelling, num_rental, num_non_res, 
        apprais_date, lot_value, building_value, value, prev_value, date_added) 
    VALUES
        (%(id)s, %(lat)s, %(lng)s, %(point)s, %(lot_id)s, %(lot_geom)s, %(year)s, %(muni)s, %(muni_code)s, 
        %(arrond)s, %(address)s, %(street_name)s, %(mat18)s, %(cubf)s, %(nghbr_unit)s, %(owner_date)s, 
        %(owner_type)s, %(owner_status)s, %(lot_lin_dim)s, %(lot_area)s, %(max_floors)s, %(const_yr)s, 
        %(const_yr_real)s, %(floor_area)s, %(phys_link)s, %(const_type)s, %(num_dwelling)s, %(num_rental)s, 
        %(num_non_res)s, %(apprais_date)s, %(lot_value)s, %(building_value)s, %(value)s, 
        %(prev_value)s, %(date_added)s) ON CONFLICT DO NOTHING"""

SQL_GET_DUPLICATES = f"""select * from {EVALUNIT_TABLE} 
    WHERE lat = %s and lng = %s and address = %s and muni = %s;"""

# The parentheses around %s are important here
SQL_DELETE_DUPLICATES = f"""DELETE FROM {EVALUNIT_TABLE} WHERE id in (%s)"""


class Command(BaseCommand):
    help = """Aggregate individually listed MURBs into single entries representing one builing. 
        This needs to be run after the roll shapefile has been processed as it uses the location of MURBs."""

    def add_arguments(self, parser):
        
        parser.add_argument('-n', '--num-workers', 
                            type=int, 
                            default=os.cpu_count() - 1, 
                            help="Number of parallel workers. Defaults to one less than the number of CPUs.")
        
        parser.add_argument('-t', '--test', 
                            action='store_true', 
                            default=False,
                            help="Run in testing mode (won't delete units without coords after)")


    def handle(self, *args, **options):
        t0 = datetime.now()

        test = options['test']
        num_workers = options['num_workers']

        create_disaggregated_MURBs_table_if_not_exists()

        duplicated = get_duplicated_MURBs()

        # Shorten the working data for testing        
        if test:
            duplicated = duplicated[0:num_workers * 10]

        self.stdout.write(f'{len(duplicated)} duplicated MURBs found.')
        
        try:
            launch_jobs(duplicated, num_workers)
            self.stdout.write(
                self.style.SUCCESS(f'\nFinished aggregating MURBs in {datetime.now() - t0} s')
            )
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.ERROR('\nInterrupt received')
            )



def launch_jobs(duplicates: list, num_workers: int):

    splits = split_list_in_n(duplicates, num_workers)

    # Doesn't work without the initializer function
    # https://stackoverflow.com/questions/73295496/django-how-can-i-use-multiprocessing-in-a-management-command
    with Pool(processes=num_workers, initializer=django.setup) as pool:
        pool.map(aggregate_murbs, splits)

    # # Once we're done aggregating and deleting the extra MURBs,
    # # then we can create the foreign key constraint on the aggregated MURB table
    # conn, cursor = get_DB_conn(DB_CONN_STR)
    # cursor.execute(f"""
    #     ALTER TABLE {MURB_DISAG_TABLE} ADD FOREIGN KEY(agg_id) REFERENCES {EVALUNIT_TABLE}(id);
    # """)
    # conn.commit()
    # conn.close()

    
def get_duplicated_MURBs():
    conn, cursor = get_DB_conn(DB_CONN_STR)

    # Get all MURBs (CUBF == 1000) with duplicated entries for lat,lng,address,muni
    cursor.execute(f"""SELECT address, muni, lat, lng, count(*) as num_duplicates, sum(num_dwelling) as sum_dwellings 
    FROM {EVALUNIT_TABLE} WHERE cubf = 1000 group by lat, lng, address, muni having count(*) > 1 
    ORDER BY count(*) ASC;""")

    duplicated = cursor.fetchall()
    conn.close()
    return duplicated



def aggregate_murbs(data):
    conn, cursor = get_DB_conn(DB_CONN_STR)

    worker_id = data['id']
    duplicated_murbs = data['data']

    for i, murb in tqdm(enumerate(duplicated_murbs), desc=f"Worker {worker_id}", 
                       total=len(duplicated_murbs), position=worker_id, leave=False
    ):
        try:
            # get duplicates using the key
            lat, lng, address, muni = murb['lat'], murb['lng'], murb['address'], murb['muni']
            
            # Fetch duplicates
            cursor.execute(SQL_GET_DUPLICATES, (lat, lng, address, muni))
            duplicates = cursor.fetchall()

            if len(duplicates) < 1:
                continue

            dupe_ids = []

            # For getting the most frequent
            years = []
            nghbr_units = []
            owner_dates = []
            owner_types = []
            owner_statuses = []
            const_years = []
            const_years_real = []
            apprais_dates = []

            # For summing
            num_rentals = 0
            num_non_res = 0

            # For averaging
            lot_lin_dims = []
            lot_areas = []
            floor_areas = []
            lot_values = []
            building_values = []
            values = []
            prev_values = []

            max_apt_num = 0

            for dupe in duplicates:

                # Gather all IDs to delete them after
                dupe_ids.append((dupe['id'],))

                # Gather most frequent nghbr_unit, owner_type, status, const_yr, yr_real_est, phys_link
                years.append(dupe['year'])
                nghbr_units.append(dupe['nghbr_unit'])
                owner_dates.append(dupe['owner_date'])
                owner_types.append(dupe['owner_type'])
                owner_statuses.append(dupe['owner_status'])
                const_years.append(dupe['const_yr'])
                const_years_real.append(dupe['const_yr_real'])
                apprais_dates.append(dupe['apprais_date'])
                
                # Average these
                if dupe['lot_lin_dim']:
                    lot_lin_dims.append(dupe['lot_lin_dim'])
                if dupe['lot_area']:
                    lot_areas.append(dupe['lot_area'])
                if dupe['floor_area']:
                    floor_areas.append(dupe['floor_area'])
                if dupe['lot_value']:
                    lot_values.append(dupe['lot_value'])
                if dupe['building_value']:
                    building_values.append(dupe['building_value'])
                if dupe['value']:
                    values.append(dupe['value'])
                if dupe['prev_value']:
                    prev_values.append(dupe['prev_value'])

                # Sum these
                if num_rental := dupe['num_rental']:
                    num_rentals += int(num_rental)
                if non_res := dupe['num_non_res']:
                    num_non_res += int(non_res)
                
                # Attempt to cast the lower apt_num to an integer
                if apt_num := dupe['apt_num_1']:
                    try:
                        max_apt_num = max(max_apt_num, int(apt_num))
                    except ValueError:
                        continue
            
            # Create a new ID for the aggregated MURB
            # We set the last 4 digits to 9999 to recognize them
            # No other IDs end with 9999 so it is safe to use.
            agg_id = dupe['id'][:-4] + '9999'
            
            agg_data = {
                'id': agg_id, 
                'lat': lat,
                'lng': lng,
                'address': address,
                # All dulicates should have the same point, lot id and geometry
                'point': dupe['point'],
                'lot_id': dupe['lot_id'],
                'lot_geom': dupe['lot_geom'],
                # All of these address fields should be the same for all duplicates, since they
                # were concatenated to form the 'address' field, which is the same for all
                'num_adr_inf': dupe['num_adr_inf'],
                'num_adr_inf_2': dupe['num_adr_inf_2'],
                'num_adr_sup': dupe['num_adr_sup'],
                'num_adr_sup_2': dupe['num_adr_sup_2'],
                'street_name': dupe['street_name'],
                'apt_num': dupe['apt_num'],
                'apt_num_1': dupe['apt_num_1'],
                'apt_num_2': dupe['apt_num_2'],

                'muni': muni,
                'mat18': dupe['mat18'][:-4] + '9999', # We set the last 4 digits of the id to 9999 to recognize them
                'phys_link': '1',   # set as detached since we'll be representing the whole building
                'const_type': '5',  # full-storey 

                # Grab the values from the last duplicate - they should be the same for all
                'cubf': dupe['cubf'],
                'arrond':  dupe['arrond'],
                'muni_code':  dupe['muni_code'],
                'num_rental':  num_rentals,
                'num_non_res':  num_non_res,

                'year': Counter(years).most_common(1)[0][0],
                'nghbr_unit': Counter(nghbr_units).most_common(1)[0][0],
                'owner_date': Counter(owner_dates).most_common(1)[0][0],
                'owner_type': Counter(owner_types).most_common(1)[0][0],
                'owner_status': Counter(owner_statuses).most_common(1)[0][0],
                'const_yr': Counter(const_years).most_common(1)[0][0],
                'const_yr_real': Counter(const_years_real).most_common(1)[0][0],
                'apprais_date': Counter(apprais_dates).most_common(1)[0][0],
            
                'lot_lin_dim': _average_or_none(lot_lin_dims),
                'lot_area': _sum_or_none(lot_areas),
                'floor_area': _sum_or_none(floor_areas),
                'lot_value': _sum_or_none(lot_values),
                'building_value': _sum_or_none(building_values),
                'value': _sum_or_none(values),
                'prev_value': _sum_or_none(prev_values),

                # May overestimate for some
                'max_floors': infer_number_of_floors(max_apt_num, lat, lng),
                'num_dwelling': murb['sum_dwellings'],
                'date_added': datetime.now(),
            }

            # Write out the new aggregated MURB
            cursor.execute(SQL_INSERT_AGGREGATED_MURB, agg_data)
            conn.commit()

            # Set the foreign key of each duplicate to their aggregated version
            for dup in duplicates:
                dup['agg_id'] = agg_id
            
            # Copy the duplicates to another table
            execute_values(cursor, SQL_COPY_DUPLICATES_TO_OTHER_TABLE, duplicates, template=SQL_COPY_TEMPLATE)
            conn.commit()

            # delete all the duplicates by ID
            execute_values(cursor, SQL_DELETE_DUPLICATES, dupe_ids)
            conn.commit()

        except KeyboardInterrupt:
            return
            


def _sum_or_none(arr):
    if arr:
        return round(sum(arr), 2)
    return None

def _average_or_none(arr):
    if arr:
        return round(mean(arr), 2)
    return None


def infer_number_of_floors(max_apt_num, lat, lng):
    num_floors = 1
    # There are only 3 buildings with apt_num > 10,000
    # so we have some hard-coded logic here
    if max_apt_num >= 10_000:
        # 4040 rue de l' ÉCLUSE
        if lat == 46.7174122671 and lng == -71.2773427875:
            num_floors = 3
        else:
            num_floors = 10
    # If between 10,000 and 1,000, consider the first 2 digits to be the floor number
    elif max_apt_num >= 1000:
        num_floors = max_apt_num // 100
    # If between 1 and 1000, consider the first digit to be the floor number
    else:
        num_floors = max_apt_num // 10

    return num_floors


def create_disaggregated_MURBs_table_if_not_exists():
    """
    Create a new table to hold the disaggregated MURB units, in case we every want to query them again.
    They will then be deleted from the main table, and replaced by their aggregated entries.
    """
    conn, cursor = get_DB_conn(DB_CONN_STR)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {MURB_DISAG_TABLE} (
            id TEXT PRIMARY KEY CHECK(length(id)=23),
            agg_id TEXT NOT NULL,
            lat NUMERIC(20, 10) NOT NULL,
            lng NUMERIC(20, 10) NOT NULL,
            point GEOMETRY(POINT, 4326),
            lot_id TEXT,
            lot_geom GEOMETRY(MULTIPOLYGON, 4326),
            year SMALLINT NOT NULL,
            muni TEXT NOT NULL,
            muni_code TEXT NOT NULL,
            arrond TEXT,
            address TEXT NOT NULL,
            num_adr_inf TEXT,
            num_adr_inf_2 TEXT,
            num_adr_sup TEXT,
            num_adr_sup_2 TEXT,
            street_name TEXT,
            apt_num TEXT,
            apt_num_1 TEXT,
            apt_num_2 TEXT,
            mat18 TEXT NOT NULL CHECK(length(mat18)=18),
            cubf SMALLINT NOT NULL,
            file_num TEXT,
            nghbr_unit TEXT,
            owner_date DATE,
            owner_type TEXT,
            owner_status TEXT,
            lot_lin_dim NUMERIC(8, 2),
            lot_area NUMERIC(15, 2),
            max_floors SMALLINT,
            const_yr SMALLINT,
            const_yr_real TEXT,
            floor_area NUMERIC(8, 1),
            phys_link TEXT,
            const_type TEXT,
            num_dwelling SMALLINT,
            num_rental SMALLINT,
            num_non_res SMALLINT,
            apprais_date DATE,
            lot_value INTEGER,
            building_value INTEGER,
            value INTEGER,
            prev_value INTEGER,
            date_added DATE
        );""")
    conn.commit()
    conn.close()
    

