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
from buildings.management.commands.new_version_create_survey1_and_responses import (
    SURVEY_1_SCHEMA,
    transform_all_values,
)
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
            from buildings b 
                join responses r on r.building_id = b.id
            where (r.data->'exterior_cladding') @> '["Brick Masonry"]' and b.attrs->>'service_center' like '%Montr%'
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

    # Fetch the first survey
    survey1, _ = Survey.objects.get_or_create(
        name="Recon Survey V1", created_by=SYSTEM_USER
    )

    survey, _ = Survey.objects.get_or_create(
        name="Sub-survey Example: Montreal HLMs w brick facade",
        description="Example of a sub-survey on SHQ HLMs in Montréal with brick facade. This survey filters the SHQ HLM dataset using responses to the V1 survey. Only buildings marked as having a brick facade are included as candidates.",
        created_by=SYSTEM_USER,
        dataset=dataset,
        status=Survey.Status.ACTIVE,
        # Q Object for dataset filter
        dataset_filter={
            "condition": "AND",
            "rules": [
                {
                    "id": "attrs__service_center",
                    "field": "attrs__service_center",
                    "type": "string",
                    "operator": "equal",
                    "value": "CS Montréal",
                },
            ],
        },
        surveys_filter={
            "condition": "AND",
            "rules": [
                {
                    "id": f"s_{survey1.id}_exterior_cladding",
                    "field": f"s_{survey1.id}_exterior_cladding",
                    "operator": "in",
                    "type": "string",
                    "value": ["Brick Masonry"],
                },
            ],
        },
        schema=SURVEY_1_SCHEMA,
        modals=SURVEY_1_MODALS,
    )
    survey.save()

    metal_dataset, _ = Dataset.objects.get_or_create(
        name="Potential Metal Buildings",
        created_by=SYSTEM_USER,
    )

    survey_metal, _ = Survey.objects.get_or_create(
        name="Survey on Metal Buildings",
        description="Surveying the output of the metal building detection AI model for metal barn-like buildings.",
        created_by=SYSTEM_USER,
        dataset=metal_dataset,
        status=Survey.Status.ACTIVE,
        schema=SURVEY_1_SCHEMA,
    )
    survey_metal.save()

    print(f"Create a subsurvey and create its responses from old responses model")

    for offset in tqdm(range(0, num_units, chunk_length)):
        try:
            from_cur.execute(
                f"""select
                    r.data as data,
                    r.created_by_id,
                    r.building_id,
                    r.date_added as date_added,
                    r.date_modified as date_modified
                from buildings b 
                join responses r on r.building_id = b.id
                WHERE
                    r.survey_id = {survey1.id}
                    and (r.data->'exterior_cladding') @> '["brick_masonry"]' and b.attrs->>'service_center' like '%Montr%'
                ORDER BY r.id DESC
                LIMIT {chunk_length} offset {offset}
            """,
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
                        created_by=User.objects.get(pk=resp["created_by_id"]),
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
