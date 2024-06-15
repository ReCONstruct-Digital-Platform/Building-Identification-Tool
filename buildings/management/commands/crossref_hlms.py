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
import csv
import json
import shutil
import IPython
import django
import psycopg2
import requests
import traceback
import googlemaps
import psycopg2.extras

from tqdm import tqdm
from pathlib import Path
from datetime import datetime
from unidecode import unidecode
from collections import Counter
from multiprocessing import Pool

from django.db import connection
from django.core.management.base import BaseCommand
from buildings.utils.utility import split_list_in_n, get_DB_conn, is_streetview_imagery_available

from config.settings import BASE_DIR, GOOGLE_MAPS_API_KEY, MAPBOX_TOKEN

from buildings.utils.constants import * 
from buildings.models import HLMBuilding, EvalUnit
from buildings.utils.utility import download_file

DEFAULT_OUT = BASE_DIR / 'data' 

DB_NAME = connection.settings_dict['NAME']
DB_HOST = connection.settings_dict['HOST']
DB_PORT = connection.settings_dict['PORT']
DB_USER = connection.settings_dict['USER']
DB_PW = connection.settings_dict['PASSWORD']
DB_CONN_STR = f"postgresql://{DB_USER}:{DB_PW}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

EVALUNIT_TABLE = EvalUnit.objects.model._meta.db_table
HLM_TABLE = HLMBuilding.objects.model._meta.db_table

WAY_TYPE_VALS = list(WAY_TYPES.values())
WAY_LINK_VALS = list(WAY_LINKS.values())
CARDINAL_POINT_VALS = [c.lower() for c in CARDINAL_POINTS.values()]

URL_MAPBOX_V6 = f"https://api.mapbox.com/search/geocode/v6/forward"

SQL_UPSERT_HLM = f"""INSERT INTO {HLM_TABLE}
        (id, lat, lng, point, eval_unit_id, streetview_available, project_id, organism, service_center, address, 
        street_num, street_name, muni, postal_code, num_dwellings, num_floors, area_footprint, area_total, ivp, 
        disrepair_state, interest_adjust_date, contract_end_date, category, building_id) 
    VALUES
        (%(id)s, %(lat)s, %(lng)s, ST_SetSRID(ST_MakePoint(%(lng)s, %(lat)s), 4326), %(eval_unit_id)s, %(streetview_available)s, 
        %(project_id)s, %(organism)s, %(service_center)s, %(address)s, %(street_num)s, %(street_name)s, %(muni)s, %(postal_code)s, 
        %(num_dwellings)s, %(num_floors)s, %(area_footprint)s, %(area_total)s, %(ivp)s, %(disrepair_state)s, %(interest_adjust_date)s, 
        %(contract_end_date)s, %(category)s, %(building_id)s) 
    ON CONFLICT (id) DO UPDATE SET
        id = EXCLUDED.id, lat = EXCLUDED.lat, lng = EXCLUDED.lng, point = EXCLUDED.point, eval_unit_id = EXCLUDED.eval_unit_id, 
        streetview_available = EXCLUDED.streetview_available, project_id = EXCLUDED.project_id, organism = EXCLUDED.organism, 
        service_center = EXCLUDED.service_center, address = EXCLUDED.address, street_num = EXCLUDED.street_num, 
        street_name = EXCLUDED.street_name, muni = EXCLUDED.muni, postal_code = EXCLUDED.postal_code, 
        num_dwellings = EXCLUDED.num_dwellings, num_floors = EXCLUDED.num_floors, area_footprint = EXCLUDED.area_footprint, 
        area_total = EXCLUDED.area_total, ivp = EXCLUDED.ivp, disrepair_state = EXCLUDED.disrepair_state, 
        interest_adjust_date = EXCLUDED.interest_adjust_date, contract_end_date = EXCLUDED.contract_end_date, 
        category = EXCLUDED.category, building_id = EXCLUDED.building_id;"""


class Command(BaseCommand):
    help = "Download the HLMs and crossreference them with the EvalUnits."

    def add_arguments(self, parser):
        parser.add_argument('-o', '--output-folder', 
                            type=Path, 
                            default=DEFAULT_OUT,
                            help='Path to folder containing the roll data, or where it will be downloaded.')

        parser.add_argument('-d', '--download-data', 
                            action="store_true", 
                            default=False,
                            help="Download the HLM data")

        parser.add_argument('-dd', '--delete-data', 
                            action="store_true", 
                            default=False,
                            help="Delete the roll data after processing")
        
        parser.add_argument('-n', '--num-workers', 
                            type=int, 
                            default=2, 
                            help="Number of parallel workers. Defaults to 2.")
        
        parser.add_argument('-t', '--test', 
                            action='store_true', 
                            default=False,
                            help='Run in testing mode on a few XMLs')


    def handle(self, *args, **options):

        data_folder: Path = options['output_folder'] / Path('hlm')
        data_folder.mkdir(exist_ok=True, parents=True)

        download_data = options['download_data']
        delete_data = options['delete_data']
        num_workers = options['num_workers']
        test = options['test']
        
        t0 = datetime.now()

        # If the folder is empty
        if not list(data_folder.glob('**/*.csv')) or download_data:
            download_file("https://f005.backblazeb2.com/file/bit-data-public/hlms.csv", data_folder)

        hlm_file = next(data_folder.glob('**/*.csv'))

        create_hlms_table_if_not_exists()

        try:
            results = launch_jobs(hlm_file, num_workers, test)
            self.stdout.write(
                self.style.SUCCESS(f'\nFinished crossreferencing HLMs in {datetime.now() - t0} s')
            )
            
            overall_result = Counter()
            for result in results:
                overall_result += Counter(result)
                
            self.stdout.write(
                f"\tTotal HLMs cross-referenced: {overall_result['num_found']}")
            
            self.stdout.write(
                f"\tHLMs excluded (< 3 dwellings): {overall_result['less_than_3_dwellings']}")
            
            self.stdout.write(
            f"\tHLMs from unsupported municipalities: {overall_result['unknown_muni']}")
            
            self.stdout.write(
            f"\tMapbox API calls: {overall_result['mapbox_api_calls']}")
            
            self.stdout.write(
            f"\tGoogle API calls: {overall_result['google_api_calls']}")
            
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.ERROR('\nInterrupt received')
            )
        finally:
            if delete_data:
                shutil.rmtree(data_folder)


def launch_jobs(hlm_file, num_workers, test=False):
    csvreader = csv.reader(open(hlm_file, 'r', encoding='utf-8'))
    next(csvreader) # Skip the header
    hlms = [record for record in csvreader]
    
    if test:
        hlms = hlms[0: 25 * num_workers]

    splits = split_list_in_n(hlms, num_workers)

    with Pool(processes=num_workers, initializer=django.setup) as pool:
        results = pool.map(geocode_and_crossref_HLMs, splits)

    return results



def geocode_and_crossref_HLMs(work_split):
    conn, cursor = get_DB_conn(DB_CONN_STR)
    
    worker_id = work_split['id']
    data = work_split['data']
    num_hlms = len(data)

    gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
    
    # Get a set of all municipalities in the roll
    cursor.execute(f"""SELECT DISTINCT muni FROM {EVALUNIT_TABLE};""")
    ALL_ROLL_MUNIS = set([r['muni'] for r in cursor.fetchall()])
    # Dictionary to cache resolved munis
    HLM_ROLL_MUNI_MAP = {}
    # Set to hold munis which could not be approximately matched - missing from DB
    # We could hard code these since we know e.g a lot of northern communities are absent
    # but generating it after a failed match makes this more extendable to possible future inputs
    MISSING_MUNIS = set()

    # Two level map keeping the mapped street names
    # for each municpality
    HLM_ROLL_STREET_NAME_MAP = {}

    num_found = 0
    less_than_3_dwellings = 0
    unknown_muni = 0

    mapbox_api_calls = 0
    google_api_calls = 0

    for i, row in tqdm(enumerate(data), desc=f"Worker {worker_id}", total=num_hlms, position=worker_id, leave=False):
        try:
            hlm = parse_HLM_csv_row(row)

            # # Skip HLMs already in the DB
            # cursor.execute(f"SELECT * from {HLM_TABLE} where id = %s;", (hlm['id'],))
            # if cursor.fetchone():
            #     num_found += 1
            #     continue
            
            # Skip HLMs with less than 3 dwellings
            if hlm['num_dwellings'] < 3:
                less_than_3_dwellings += 1
                continue
            
            hlm['muni'] = resolve_municipality(hlm['muni'], ALL_ROLL_MUNIS, HLM_ROLL_MUNI_MAP, MISSING_MUNIS)
            if hlm['muni'] is None:
                unknown_muni += 1
                continue
            muni_clean = hlm['muni'].replace('\'', '\'\'')

            # The street names are cutoff after 21 characters in the SHQ CSV
            # for entries with 21 characters, resolve the street name by doing a
            # fuzzy search with the roll DB. This is not a perfect process!
            if len(hlm['street_name']) == 21:
                # Take SHQ file street names and find their equivalent in the roll
                resolved_street_name = resolve_street_name(hlm['street_name'], muni_clean, HLM_ROLL_STREET_NAME_MAP)

                if resolved_street_name:
                    hlm['street_name'] = resolved_street_name
            
            # Geocode the HLM 
            # We try Google first as it's better than Mapbox from my experience, 
            # at least with HLMs in less populated regions of Quebec
            # we fall back to using mapbox, though its unlikely Mpabox will have a good result
            # if Google did not find it already
            point = geocode_with_gmaps(hlm, gmaps)
            
            if point:
                google_api_calls += 1

            # If no match was found, or the match confidence is weak,
            # we try again with the Mapbox geocoding API
            else:
                point = geocode_with_mapbox(hlm)
            
            # Now that we have a point, we attempt to
            # fetch the lot that contains the point.
            if point:
                mapbox_api_calls += 1
                # First verify that streetview imagery is available at the point
                hlm['streetview_available'] = is_streetview_imagery_available(point['coordinates'][1], point['coordinates'][0])

                # We filter out the CUBFs related to parcs
                # the deocoded pin could be there but it's unlikely to be the HLM
                cursor.execute(f"""SELECT id FROM {EVALUNIT_TABLE} 
                               WHERE ST_Intersects(lot_geom, ST_GeomFromGeoJson(%s)) 
                               AND cubf != 7611;""", (json.dumps(point),))

                if res := cursor.fetchone():
                    hlm['eval_unit_id'] = res['id']
                    cursor.execute(SQL_UPSERT_HLM, hlm)
                    conn.commit()
                    num_found += 1
                    continue

                
                # Search by proximity to the HLM point
                # We'll go through 5 and verify if the street numbers are the same
                # as sometimes we end up on the wrong side of the street!
                # https://postgis.net/documentation/faq/radius-search/
                cursor.execute(f"""SELECT id, num_adr_inf, num_adr_sup FROM {EVALUNIT_TABLE} 
                               WHERE ST_DWITHIN(lot_geom, ST_SETSRID(ST_GeomFromGeoJSON(%s), 4326), 0.001)
                               AND cubf != 7611 
                               ORDER BY ST_DISTANCE(lot_geom, ST_SETSRID(ST_GeomFromGeoJSON(%s), 4326)) 
                               ASC LIMIT 5;""", (json.dumps(point), json.dumps(point),))
                
                # We go over the top 5 closest lots 3 times, in order of decending match quality
                # As soon as we find a match we break out of the loops 
                found = False
                if results := cursor.fetchall():
                    # Street number could have a second string part
                    street_num, _ = separate_num_adr(hlm['street_num'])
                    # Try 1: Match on the (inferior) street number
                    for res in results:
                        if res['num_adr_inf'] == street_num:
                            hlm['eval_unit_id'] = res['id']
                            cursor.execute(SQL_UPSERT_HLM, hlm)
                            conn.commit()
                            num_found += 1
                            found = True
                            break
                    
                    if found: continue

                    # Try 2: If the eval units have a superior street number,
                    # find the unit such that the hlm's street number is contained
                    # within the range AND of the same parity as the inferior street number
                    # This is a heuristic for being on the same side of the street
                    for res in results:
                        num_adr_inf, _ = separate_num_adr(res['num_adr_inf'])
                        num_adr_sup, _ = separate_num_adr(res['num_adr_sup'])
                        
                        if num_adr_sup and num_adr_inf <street_num < num_adr_sup:
                            if (num_adr_inf % 2 == 0 and street_num % 2 == 0) or (num_adr_inf % 2 == 1 and street_num % 2 == 1):
                                hlm['eval_unit_id'] = res['id']
                                cursor.execute(SQL_UPSERT_HLM, hlm)
                                conn.commit()
                                num_found += 1
                                found = True
                                break

                    if found: continue

                    # Try 3: Match on the eval units such that the hlm street
                    # number is within the range without caring about parity. 
                    for res in results:
                        num_adr_inf, _ = separate_num_adr(res['num_adr_inf'])
                        num_adr_sup, _ = separate_num_adr(res['num_adr_sup'])

                        if num_adr_sup and num_adr_inf < street_num < num_adr_sup:
                            hlm['eval_unit_id'] = res['id']
                            cursor.execute(SQL_UPSERT_HLM, hlm)
                            conn.commit()
                            num_found += 1
                            continue


                # Final attempt, just match the addresses with evalunits table, we get a few this way
                cursor.execute(f"""SELECT e.id FROM {HLM_TABLE} h 
                               JOIN {EVALUNIT_TABLE} e ON lower(e.address) = lower(%s) 
                               WHERE h.eval_unit_id is null;""", (hlm['address'],))
                if res := cursor.fetchone():
                    hlm['eval_unit_id'] = res['id']
                    cursor.execute(SQL_UPSERT_HLM, hlm)
                    conn.commit()
                    num_found += 1
                    continue

        except KeyboardInterrupt:
            return {
                'num_found': num_found,
                'unknown_muni': unknown_muni,
                'less_than_3_dwellings': less_than_3_dwellings,
                'google_api_calls': google_api_calls,
                'mapbox_api_calls': mapbox_api_calls
            }
        except:
            exc = traceback.format_exc()
            print(exc)
            IPython.embed()
            print(row)
            conn.reset()
            continue

    conn.commit()
    return {
        'num_found': num_found,
        'unknown_muni': unknown_muni,
        'less_than_3_dwellings': less_than_3_dwellings,
        'google_api_calls': google_api_calls,
        'mapbox_api_calls': mapbox_api_calls
    }


def geocode_with_gmaps(hlm, gmaps):
    gmaps_query = ' '.join([hlm['street_num'], hlm['street_name'], hlm['muni'], 'QC', hlm['postal_code']])
    geocode_result = gmaps.geocode(gmaps_query)

    if len(geocode_result) == 0:
        # Could not geocode using google maps
        return None

    geocode_result = geocode_result[0]

    if 'location_type' in geocode_result['geometry'] and geocode_result['geometry']['location_type'] in ['ROOFTOP', 'RANGE_INTERPOLATED']:
        for component in geocode_result['address_components']:
            if 'street_number' in component['types']:
                hlm['street_num'] = component['long_name']
            
            if 'route' in component['types']:
                hlm['street_name'] = component['long_name']
        
        hlm['address'] =  hlm['street_num'] + ' ' + hlm['street_name']
        hlm['lng'] = geocode_result['geometry']['location']['lng']
        hlm['lat'] = geocode_result['geometry']['location']['lat']

        return {
            'type': 'Point',
            'coordinates': [hlm['lng'], hlm['lat']]
        }
    
    # If we only have a partial match, return early
    elif 'partial_match' in geocode_result and geocode_result['partial_match'] is True:
        return None
    else:
        # Check the returned data for a street number
        # If absent, it has matched a street or other and we should discard
        for component in geocode_result['address_components']:
            if 'street_number' in component['types']:
                hlm['street_num'] = component['long_name']
            
            if 'route' in component['types']:
                hlm['street_name'] = component['long_name']

        if hlm['street_num'] is None:
            return None

        hlm['address'] = hlm['street_num'] + ' ' + hlm['street_name']
        hlm['lng'] = geocode_result['geometry']['location']['lng']
        hlm['lat'] = geocode_result['geometry']['location']['lat']

        return {
            'type': 'Point',
            'coordinates': [hlm['lng'], hlm['lat']]
        }


def geocode_with_mapbox(hlm):

    mapbox_resp = mapbox_query_v6(hlm, MAPBOX_TOKEN)

    if mapbox_resp.ok:
        mapbox_result = mapbox_resp.json()

        if len(mapbox_result['features']) > 0:
            match_confidence = mapbox_result['features'][0]['properties']['match_code']['confidence']

            if match_confidence in ['high', 'exact']:
                point = mapbox_result['features'][0]['geometry']
                hlm['lng'] = point['coordinates'][0]
                hlm['lat'] = point['coordinates'][1]

                # Save the "official" data returned as it's more likely correct
                # and better formatted than the cutoff HLM data or the no-accent roll data
                if 'context' in mapbox_result['features'][0]['properties'] and 'address' in mapbox_result['features'][0]['properties']['context']:
                    hlm['address'] = mapbox_result['features'][0]['properties']['context']['address']['name']
                    hlm['street_name'] = mapbox_result['features'][0]['properties']['context']['address']['street_name']
                    hlm['street_num'] = mapbox_result['features'][0]['properties']['context']['address']['address_number']
                
                return point
    return None

def parse_HLM_csv_row(row):

    num_adr_inf, num_adr_inf_2 = separate_num_adr(row[4])
    if num_adr_inf_2:
        street_num = f"{num_adr_inf} {num_adr_inf_2}"
    else:
        street_num = str(num_adr_inf)

    return {
        'id': row[0],
        'project_id': row[1],
        'organism': row[2],
        'service_center': row[3],
        'street_num': street_num,
        'street_name': row[5],
        'muni': row[6],
        # 'province': row[7],
        'postal_code': row[8],
        'num_dwellings': int(row[9]),
        # 'num_floors_above_first': row[10],
        'num_floors': int(row[11]),
        'area_footprint': float(row[12].replace(',', '.')),
        'area_total': float(row[13].replace(',', '.')),
        'ivp': float(row[14].replace(',', '.').replace('%', '')),
        'disrepair_state': row[15],
        'interest_adjust_date': row[16],
        'contract_end_date': row[17] if row[17] != '#N/A' else None,
        'category': row[19],
        'building_id': row[20],
    }


def create_hlms_table_if_not_exists():
    conn = psycopg2.connect(DB_CONN_STR)
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {HLM_TABLE} (
            id INTEGER PRIMARY KEY,
            lat NUMERIC(20, 10) NOT NULL,
            lng NUMERIC(20, 10) NOT NULL,
            point GEOMETRY(POINT, 4326),
            eval_unit_id TEXT REFERENCES {EVALUNIT_TABLE}(id),
            streetview_available BOOLEAN NOT NULL,
            project_id INTEGER NOT NULL,
            organism TEXT NOT NULL,
            service_center TEXT,
            address TEXT,
            street_num TEXT,
            street_name TEXT,
            muni TEXT,
            postal_code TEXT,
            num_dwellings INTEGER,
            num_floors INTEGER,
            area_footprint NUMERIC(8,2),
            area_total NUMERIC(8,2),
            ivp NUMERIC(8,2),
            disrepair_state TEXT,
            interest_adjust_date DATE,
            contract_end_date DATE,
            category TEXT,
            building_id INTEGER
        );""")
    conn.commit()
    conn.close()


def sanitize_street_name(street_name):
    """
    Remove any kind of way type, link and cardinal direction from the street name
    """
    street_name = street_name.lower()

    for way_type in WAY_TYPE_VALS:
        if way_type in street_name:
            street_name = street_name.replace(way_type, '')

    for way_link in WAY_LINK_VALS:
        if way_link in street_name:
            street_name = street_name.replace(way_link, '')
    
    if street_name.split(' ')[-1] in CARDINAL_POINT_VALS:
        street_name = ' '.join(street_name.split(' ')[:-1])

    # Escape single quotes for PSQL
    street_name = street_name.replace('\'', '\'\'')

    # remove accents
    street_name = unidecode(street_name).strip()

    return street_name


def separate_num_adr(street_designation: str):

    if street_designation is None:
        return None, None
    
    if street_designation.isdigit():
        return int(street_designation), None
    
    num_adr_inf = ''
    for c in street_designation:
        # Here we assume the numbers will always be first
        if c.isdigit():
            num_adr_inf += c
        else:
            break
    # Lots of possible things
    # can have a '-', other part can be a letter or a number
    # just try to sanitize reasonably
    num_adr_inf_2 = street_designation.replace(num_adr_inf, '')
    num_adr_inf_2.replace('-', '')

    if num_adr_inf.isdigit():
        return int(num_adr_inf), num_adr_inf_2
    else:
        return '', num_adr_inf_2


def resolve_municipality(hlm_muni: str, ALL_ROLL_MUNIS: set, HLM_ROLL_MUNI_MAP: set, MISSING_MUNIS: set):

    _, cursor = get_DB_conn(DB_CONN_STR)

    # If the municipality matches one in the DB, we're OK
    if hlm_muni in ALL_ROLL_MUNIS:
        return hlm_muni

    # Return from cache if present
    if hlm_muni in HLM_ROLL_MUNI_MAP:
        return HLM_ROLL_MUNI_MAP[hlm_muni]
    
    # These munis are not in the DB, skip them
    if hlm_muni in MISSING_MUNIS:
        return None

    # First match the municipality of the HLM to one in the Roll.
    # A lot of northern ones are entirely absent form the DB
    # while others are spelled differently/cut-off before the end.
    hlm_muni_clean = hlm_muni.replace('\'', '\'\'')

    # Try to find the closest match
    # and cache the result for later
    cursor.execute(f"""SELECT muni, SIMILARITY(muni, '{hlm_muni_clean}') FROM {EVALUNIT_TABLE} 
                    WHERE muni % '{hlm_muni_clean}' ORDER BY SIMILARITY(muni, '{hlm_muni_clean}') DESC LIMIT 1;""")
    result = cursor.fetchone()

    if result:
        HLM_ROLL_MUNI_MAP[hlm_muni] = result['muni']
        return result['muni']

    # Could not find a match with > 0.3 similarity
    else:
        MISSING_MUNIS.add(hlm_muni)
        return None


def resolve_street_name(hlm_street_name, muni_clean, HLM_ROLL_STREET_NAME_MAP):
    """
    We have to resolve street names because the SHQ CSV file cuts fields off after 21 characters!
    """
    _, cursor = get_DB_conn(DB_CONN_STR)

    hlm_street_name = hlm_street_name.replace('\'', '\'\'')

    # Return from cache if present
    if hlm_street_name in HLM_ROLL_STREET_NAME_MAP:
        return HLM_ROLL_STREET_NAME_MAP[hlm_street_name]

    # Try to match the street_name as is
    cursor.execute(f"""SELECT street_name 
                    FROM {EVALUNIT_TABLE} WHERE muni = '{muni_clean}' 
                    AND lower(street_name) like lower('%{hlm_street_name}%') LIMIT 1;""")

    if res := cursor.fetchone():
        HLM_ROLL_STREET_NAME_MAP[hlm_street_name] = res['street_name']
        return res['street_name']
    
    # Remove all way types, directions, etc. from the street name
    # and try matching again
    street_name = sanitize_street_name(hlm_street_name)

    cursor.execute(f"""SELECT street_name 
                FROM {EVALUNIT_TABLE} WHERE muni = '{muni_clean}' 
                AND lower(street_name) like lower('%{street_name}%') LIMIT 1;""")

    if res := cursor.fetchone():
        HLM_ROLL_STREET_NAME_MAP[hlm_street_name] = res['street_name']
        return res['street_name']
    
    cursor.execute(f"""SELECT street_name, SIMILARITY(street_name, '{street_name}') 
                FROM {EVALUNIT_TABLE} 
                    WHERE muni = '{muni_clean}' and street_name % '{street_name}' 
                    ORDER BY SIMILARITY(street_name, '{street_name}') DESC LIMIT 1;""")
    res = cursor.fetchone()

    if res := cursor.fetchone():
        HLM_ROLL_STREET_NAME_MAP[hlm_street_name] = res['street_name']
        return res['street_name']

    return None


def mapbox_query_v6(hlm, mapbox_token):
    # In practice, using postal code and region resulted in less matches
    # See https://docs.mapbox.com/api/search/geocoding-v6/#forward-geocoding-with-structured-input
    params = {
        'access_token': mapbox_token,
        'limit': '1',
        'proximity': "-72.9722258594702,46.46566109584455", # hardcoded mtl
        "types": "address",
        "autocomplete": "false",
        "address_number": hlm['street_num'],
        "street": hlm['street_name'],
        "place": hlm['muni'],
    }
    
    return requests.get(URL_MAPBOX_V6, params=params)

