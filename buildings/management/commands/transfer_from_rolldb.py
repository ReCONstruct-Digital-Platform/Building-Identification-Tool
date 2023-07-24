import psycopg2
import psycopg2.extras
from buildings.models import Building
  
from django.core.management.base import BaseCommand

DB_USER='postgres'
DB_PASSWORD='Gr33ssp0st44$$'
DB_NAME='qc_roll_22'
ROLL_TABLE_NAME='roll'
OWNER_STATUS_TABLE_NAME='owner_status'
PHYS_LINK_TABLE_NAME='phys_link'
CONST_TYPE_TABLE_NAME='const_type'
MURB_DISAG_TABLE_NAME='murb_disag'

class Command(BaseCommand):
    help = "Transfer buildings from the property roll SQL db to BIT's DB."

    def add_arguments(self, parser):
        parser.add_argument('-n', '--number', default=1000)


    def handle(self, *args, **options):
        num_results = options['number']

        conn = psycopg2.connect(user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
        cursor = conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)

        cursor.execute(f"""SELECT id, lat, lng, year, muni, muni_code, arrond, address, 
            way_type, way_link, street_name, cardinal_pt, apt_num, mat18, cubf, 
            file_num, nghbr_unit, owner_date, owner_type, owner_status, lot_lin_dim, lot_area, max_floors, 
            const_yr, const_yr_real, floor_area, phys_link, const_type, num_dwelling, num_rental, num_non_res, 
            apprais_date, lot_value, building_value, value, prev_value 
            FROM {ROLL_TABLE_NAME} WHERE cubf = 1000 and num_dwelling > 3 and num_dwelling < 30 and const_yr < 2000 ORDER BY num_dwelling desc LIMIT {num_results}""")
        
        results = cursor.fetchall()

        for i, res in enumerate(results):
            if i % 100 == 0:
                print(f'On building {i}')
            Building(
                lat=res['lat'],
                lon=res['lng'],
                locality=res['muni'],
                formatted_address=res['address'],
                cubf=res['cubf'],
                lin_dim=res['lot_lin_dim'],
                area=res['lot_area'],
                max_num_floor=res['max_floors'],
                construction_year=res['const_yr'],
                year_real_esti=res['const_yr_real'],
                floor_area=res['floor_area'],
                type_const=res['const_type'],
                num_dwell=res['num_dwelling'],
                num_rental=res['num_rental'],
                num_non_res=res['num_non_res'],
                value_prop=res['value'],
            ).save()

