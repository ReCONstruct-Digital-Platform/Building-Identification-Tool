"""
Download the [HLM dataset](https://f005.backblazeb2.com/file/bit-data-public/hlms.csv). 
This dataset was requested from the SHQ and contains a list of all their HLMs in Quebec, along with their IVP, 
a measure of the investment necessary to do all scheduled work on a building in the next 5 years, 
expressed as a percentage of the building's currently value.

For more details, see:
- http://www.habitation.gouv.qc.ca/fileadmin/internet/documents/partenaires/guides/guide-immeuble-supplement1-section02.pdf
- http://www.habitation.gouv.qc.ca/fileadmin/internet/documents/partenaires/guides/guide_imm_section1.pdf

We want to geocode the HLM addresses, which means obtaining lat/lng coordinates for each of them. 
Using these coordinates, we will link them to an evaluation unit, by checking the intersection with a lot polygon.
"""
import os
import time
import django
import psycopg2
import traceback
import psycopg2.extras

from tqdm import tqdm
from datetime import datetime
from multiprocessing import Pool

from django.db import connection
from psycopg2.extras import execute_values
from django.core.management.base import BaseCommand
from buildings.utils.utility import NetworkError, split_list_in_n, get_DB_conn, is_streetview_imagery_available


from buildings.models import EvalUnit


DB_NAME = connection.settings_dict['NAME']
DB_HOST = connection.settings_dict['HOST']
DB_PORT = connection.settings_dict['PORT']
DB_USER = connection.settings_dict['USER']
DB_PW = connection.settings_dict['PASSWORD']
DB_CONN_STR = f"postgresql://{DB_USER}:{DB_PW}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

RESULTS_TABLE = 'sv_avail'
EVALUNIT_TABLE = EvalUnit.objects.model._meta.db_table

# This list will be given to the SQL
# Only the potential metal buildings for now
# The HLMs have their streetview availability checked separately when cross referencing them
# and we skip the other residential buildings as there are too many of them
CUBFS_TO_PROCESS = "(6811, 6812, 6813, 6814, 6815, 6816, 7219, 7221, 7222, 7223, 7224, 7225, 7229, 7233, 7239, 7290, 7311, 7312, 7313, 7314, 7392, 7393, 7394, 7395, 7396, 7397, 7399, 7411, 7412, 7413, 7414, 7415, 7416, 7417, 7418, 7419, 7421, 7422, 7423, 7424, 7425, 7429, 7431, 7432, 7433, 7441, 7442, 7443, 7444, 7445, 7446, 7447, 7448, 7449, 7451, 7452, 7459, 7491, 7492, 7493, 7499, 7611)"

SQL_UPSERT_RESULT = f"""INSERT INTO {RESULTS_TABLE}
    (id, avail) 
    VALUES %s 
    ON CONFLICT (id) DO UPDATE SET
        id = EXCLUDED.id, avail = EXCLUDED.avail;"""

SQL_UPSERT_TEMPLATE = "(%(id)s, %(avail)s)"

class Command(BaseCommand):
    help = "Go through evalunits and check if streetview images are evailable for each of them, storing the results in a table."

    def add_arguments(self, parser):
        
        parser.add_argument('-n', '--num-workers', 
                            type=int, 
                            default=os.cpu_count() - 1, 
                            help="Number of parallel workers. Defaults to CPU count - 1")
        

    def handle(self, *args, **options):

        num_workers = options['num_workers']
        
        t0 = datetime.now()

        create_results_table_if_not_exists()

        try:
            launch_jobs(num_workers)
            self.stdout.write(
                self.style.SUCCESS(f'\nFinished checking streetview availability in {datetime.now() - t0} s')
            )
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.ERROR('\nInterrupt received')
            )
            exit()


def launch_jobs(num_workers):
    conn, cursor = get_DB_conn(DB_CONN_STR, dict_cursor=False)
    cursor.execute(f'select id, lat, lng from {EVALUNIT_TABLE} where cubf in {CUBFS_TO_PROCESS};')
    all_ids = cursor.fetchall()
    conn.close()

    splits = split_list_in_n(all_ids, num_workers)

    with Pool(processes=num_workers, initializer=django.setup) as pool:
        pool.map(check_streetview_availability, splits)



def check_streetview_availability(work_split):
    conn, cursor = get_DB_conn(DB_CONN_STR)
    
    worker_id = work_split['id']
    data = work_split['data']
    num_units = len(data)

    # Exponential backoff if network calls fail
    sleep_time = 1
    max_sleep = 60

    results = []

    progress_bar = tqdm(total=num_units, desc=f"Worker {worker_id}", position=worker_id, leave=False)
    
    for i, (id, lat, lng) in enumerate(data):
        try:
            results.append({'id': id, 'avail': is_streetview_imagery_available(lat, lng)})

            if i % 100 == 0 and i > 0:
                execute_values(cursor, SQL_UPSERT_RESULT, results, template=SQL_UPSERT_TEMPLATE)
                conn.commit()
                progress_bar.update(100)

        except KeyboardInterrupt:
            progress_bar.close()
            return
        except NetworkError:
            time.sleep(sleep_time)
            sleep_time *= 2
            if sleep_time > max_sleep:
                print('Could not reach metadata API')
                exit()
        except:
            print(traceback.format_exc())
            conn.reset()
            continue

    conn.commit()
    progress_bar.close()



def create_results_table_if_not_exists():
    conn = psycopg2.connect(DB_CONN_STR)
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {RESULTS_TABLE} (
            id TEXT PRIMARY KEY,
            avail BOOLEAN NOT NULL
        );""")
    conn.commit()
    conn.close()
