import json
import math
import traceback
import IPython
import argparse
import psycopg2

from tqdm import tqdm
from dotenv import dotenv_values
from django.contrib.gis.geos import Point
from psycopg2.extras import execute_values
from django.core.management.base import BaseCommand
from buildings.models.models import User
from buildings.models.newmodels import Building, Dataset, Response, Survey
from buildings.management.constants import *

# Read in the database configuration from a .env file
ENV = dotenv_values(".env")


EVALUNITS_TABLE = "evalunits"
RESPONSES_TABLE = "responses"
HLM_TABLE = "hlms"


SQL_UPSERT_RESPONSE = f"""INSERT INTO {RESPONSES_TABLE} 
        (ext_id, lat, lng, point, dataset, address, street_name, street_num, street_num2,
        apt_num, apt_num_2, muni, submuni, postal_code, const_year, num_floors, floor_area, attrs) 
    VALUES %s
    ON CONFLICT (lat, lng, dataset, address) DO UPDATE SET
        ext_id = EXCLUDED.ext_id, lat = EXCLUDED.lat, lng = EXCLUDED.lng, point = EXCLUDED.point, dataset = EXCLUDED.dataset, address = EXCLUDED.address, street_name = EXCLUDED.street_name, street_num = EXCLUDED.street_num, street_num2 = EXCLUDED.street_num2, apt_num = EXCLUDED.apt_num, apt_num_2 = EXCLUDED.apt_num_2, muni = EXCLUDED.muni, submuni = EXCLUDED.submuni, postal_code = EXCLUDED.postal_code, const_year = EXCLUDED.const_year, num_floors = EXCLUDED.num_floors, floor_area = EXCLUDED.floor_area, attrs = EXCLUDED.attrs"""

SQL_UPSERT_BUILDING_TEMPLATE = f"""(%(ext_id)s, %(lat)s, %(lng)s, %(point)s, %(dataset)s, %(address)s, %(street_name)s, %(street_num)s, %(street_num2)s, %(apt_num)s, %(apt_num_2)s, %(muni)s, %(submuni)s, %(postal_code)s, %(const_year)s, %(num_floors)s, %(floor_area)s, %(attrs)s)"""


def transform_old_value_to_new(observed_val, VALUES_MAP):
    """
    Changed the values to be equal to the labels which makes old responses invalid
    """
    if observed_val in VALUES_MAP:
        return VALUES_MAP[observed_val]
    else:
        return observed_val


def transform_all_values(values, VALUES_MAP):
    if isinstance(values, list):
        new_vals = []
        for observed_val in values:
            if new_val := transform_old_value_to_new(observed_val, VALUES_MAP):
                new_vals.append(new_val)
        return new_vals


def migrate_responses(dry_run=True):

    from_db = psycopg2.connect(
        user=ENV["POSTGRES_USER"],
        password=ENV["POSTGRES_PW"],
        database=ENV["POSTGRES_NAME"],
        port=ENV["POSTGRES_PORT"],
        host=ENV["POSTGRES_HOST"],
    )
    # Do stuff inside the context manager block
    from_cur = from_db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    from_cur.execute(
        f"""select count(*) 
            from buildings_surveyv1 s 
            join buildings_vote v on s.vote_id = v.id 
            join hlms h on h.eval_unit_id = v.eval_unit_id 
            join buildings b on b.address = h.address
        """
    )
    num_units = from_cur.fetchone()["count"]

    NUM_CHUNKS = 1
    chunk_length = math.ceil(num_units / NUM_CHUNKS)

    SYSTEM_USER = User.objects.get(pk=33)

    dataset, _ = Dataset.objects.get_or_create(
        name="SHQ HLMs",
        description="Set of HLMs in Quebec managed by the SHQ.",
        created_by=SYSTEM_USER,
    )

    survey, _ = Survey.objects.get_or_create(
        name="Recon Survey V1",
        description="Reconstruct's initial survey to find good deep energy retrofit candidates among HLMs",
        status=Survey.Status.ACTIVE,
        created_by=SYSTEM_USER,
        dataset=dataset,
        schema=SURVEY_1_SCHEMA,
        modals=SURVEY_1_MODALS,
    )
    survey.save()

    print("Create survey1 and migrate responses")

    for offset in tqdm(range(0, num_units, chunk_length)):
        try:
            from_cur.execute(
                f"""select
                        s.*,
                        v.user_id as user_id,
                        v.date_added as date_added,
                        v.date_modified as date_modified,
                        b.id as building_id
                    from buildings_surveyv1 s 
                    join buildings_vote v on s.vote_id = v.id 
                    join hlms h on h.eval_unit_id = v.eval_unit_id 
                    join buildings b on b.address = h.address
                ORDER BY v.id DESC
                LIMIT {chunk_length} offset {offset}
            """
            )
            responses_batch = from_cur.fetchall()

            responses_to_write = []

            # Convert to new model
            for resp in responses_batch:

                data = {
                    "self_similar_cluster": resp["self_similar_cluster"],
                    "has_simple_footprint": resp["has_simple_footprint"],
                    "has_simple_volume": resp["has_simple_volume"],
                    "num_storeys": resp["num_storeys"],
                    "has_basement": resp["has_basement"],
                    "site_obstructions": transform_all_values(
                        resp["site_obstructions"], SITE_OBSTRUCTIONS
                    ),
                    "appendages": transform_all_values(resp["appendages"], APPENDAGES),
                    "exterior_cladding": transform_all_values(
                        resp["exterior_cladding"], FACADE_MATERIALS
                    ),
                    "facade_condition": resp["facade_condition"],
                    "window_wall_ratio": resp["window_wall_ratio"],
                    "large_irregular_windows": transform_all_values(
                        resp["large_irregular_windows"], WINDOWS
                    ),
                    "roof_geometry": transform_all_values(
                        resp["roof_geometry"], ROOF_GEOMETRIES
                    ),
                    "new_or_renovated": transform_all_values(
                        resp["new_or_renovated"], NEW_OR_RENOVATED
                    ),
                }

                responses_to_write.append(
                    Response(
                        data=data,
                        building=Building.objects.get(pk=resp["building_id"]),
                        survey=survey,
                        created_by=User.objects.get(pk=resp["user_id"]),
                        date_added=resp["date_added"],
                        date_modified=resp["date_modified"],
                    )
                )

            Response.objects.bulk_create(
                responses_to_write,
                update_conflicts=True,
                unique_fields=["building", "survey", "created_by"],
                update_fields=["data"],
            )

        except KeyboardInterrupt:
            print("Interrupt received")
            exit()
        except:
            print(traceback.format_exc())
            # IPython.embed()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DANGER: Modify prob DB directly")

    args = parser.parse_args()


class Command(BaseCommand):
    help = "Create new models from old evalunits"

    def add_arguments(self, parser):
        parser.add_argument("-dr", "--dry-run", action="store_true", default=True)

    def handle(self, *args, **options):
        migrate_responses(dry_run=options["dry_run"])
