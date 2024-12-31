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
from buildings.models.newmodels import Building, Dataset

# Read in the database configuration from a .env file
ENV = dotenv_values(".env")


EVALUNITS_TABLE = "evalunits"
BUILDINGS_TABLE = "buildings"
HLM_TABLE = "hlms"


SQL_UPSERT_BUILDING = f"""INSERT INTO {BUILDINGS_TABLE} 
        (ext_id, lat, lng, point, dataset, address, street_name, street_num, street_num2,
        apt_num, apt_num_2, muni, submuni, postal_code, const_year, num_floors, floor_area, attrs) 
    VALUES %s
    ON CONFLICT (lat, lng, dataset, address) DO UPDATE SET
        ext_id = EXCLUDED.ext_id, lat = EXCLUDED.lat, lng = EXCLUDED.lng, point = EXCLUDED.point, dataset = EXCLUDED.dataset, address = EXCLUDED.address, street_name = EXCLUDED.street_name, street_num = EXCLUDED.street_num, street_num2 = EXCLUDED.street_num2, apt_num = EXCLUDED.apt_num, apt_num_2 = EXCLUDED.apt_num_2, muni = EXCLUDED.muni, submuni = EXCLUDED.submuni, postal_code = EXCLUDED.postal_code, const_year = EXCLUDED.const_year, num_floors = EXCLUDED.num_floors, floor_area = EXCLUDED.floor_area, attrs = EXCLUDED.attrs"""

SQL_UPSERT_BUILDING_TEMPLATE = f"""(%(ext_id)s, %(lat)s, %(lng)s, %(point)s, %(dataset)s, %(address)s, %(street_name)s, %(street_num)s, %(street_num2)s, %(apt_num)s, %(apt_num_2)s, %(muni)s, %(submuni)s, %(postal_code)s, %(const_year)s, %(num_floors)s, %(floor_area)s, %(attrs)s)"""


def upsert_evalunits(dry_run=True):

    from_db = psycopg2.connect(
        user="bitdbuser",
        password="new_password",
        host="127.0.0.1",
        port=5432,
        database="bitdb4",
    )
    # Do stuff inside the context manager block
    from_cur = from_db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    to_db = psycopg2.connect(
        user=ENV["POSTGRES_USER"],
        password=ENV["POSTGRES_PW"],
        database=ENV["POSTGRES_NAME"],
        port=5433,
    )
    to_cur = to_db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    print(f"Upserting evalunits from local DB to prod")

    from_cur.execute(
        f"""
        SELECT count(*) 
        FROM {EVALUNITS_TABLE} e
        INNER JOIN {HLM_TABLE} h ON
            e.id = h.eval_unit_id
    """
    )
    num_units = from_cur.fetchone()["count"]

    NUM_CHUNKS = 2
    chunk_length = math.ceil(num_units / NUM_CHUNKS)

    dataset, _ = Dataset.objects.get_or_create(
        name="Potential Metal Buildings",
        description="Set of potential prefab metal buildings in Quebec. Output of a metal building detector AI model.",
        schema=[
            {
                "id": "ext_id",
                "field": "ext_id",
                "label": {"en": "External ID"},
                "type": "string",
                "input": "text",
                "optgroup": "core",
            },
            {
                "id": "address",
                "field": "address",
                "label": {"en": "Address"},
                "type": "string",
                "input": "text",
                "optgroup": "core",
            },
            {
                "id": "street_name",
                "field": "street_name",
                "label": {"en": "Street Name"},
                "type": "string",
                "input": "text",
                "optgroup": "core",
            },
            {
                "id": "street_num",
                "field": "street_num",
                "label": {"en": "Street Number"},
                "type": "string",
                "input": "text",
                "optgroup": "core",
            },
            {
                "id": "muni",
                "field": "muni",
                "label": {"en": "Municipality"},
                "type": "string",
                "input": "text",
                "optgroup": "core",
            },
            {
                "id": "submuni",
                "field": "submuni",
                "label": {"en": "Submunicipality"},
                "type": "string",
                "input": "text",
                "optgroup": "core",
            },
            {
                "id": "postal_code",
                "field": "postal_code",
                "label": {"en": "Postal Code"},
                "type": "string",
                "input": "text",
                "optgroup": "core",
            },
            {
                "id": "const_year",
                "field": "const_year",
                "label": {"en": "Construction Year"},
                "type": "date",
                "plugin": "datepicker",
                "plugin_config": {
                    "format": "yyyy",
                    "todayBtn": "linked",
                    "todayHighlight": True,
                    "autoclose": True,
                    "minViewMode": "years",
                },
                "optgroup": "core",
            },
            {
                "id": "num_floors",
                "field": "num_floors",
                "label": {"en": "Num. Floors"},
                "type": "integer",
                "input": "number",
                "optgroup": "core",
            },
            {
                "id": "floor_area",
                "field": "floor_area",
                "label": {"en": "Floor area"},
                "optgroup": "core",
                "type": "double",
                "input": "number",
                "validation": {"min": 0, "step": 0.01},
            },
            {
                "id": "attrs__p_bldg",
                "field": "attrs__p_bldg",
                "label": {"en": "Prob. Building"},
                "optgroup": "attributes",
                "type": "double",
                "input": "number",
                "validation": {"min": 0, "step": 0.01},
            },
            {
                "id": "attrs__p_metal",
                "field": "attrs__p_metal",
                "label": {"en": "Prob. Metal"},
                "optgroup": "attributes",
                "type": "double",
                "input": "number",
                "validation": {"min": 0, "step": 0.01},
            },
            {
                "id": "attrs__phys_link",
                "field": "attrs__phys_link",
                "label": {"en": "Physical Link"},
                "type": "string",
                "input": "checkbox",
                "values": [
                    "row house (one side)",
                    "semi-detached",
                    "single-detached",
                    "integrated",
                    "row house",
                ],
                "operators": ["in", "not_in"],
                "optgroup": "attributes",
            },
            {
                "id": "attrs__const_type",
                "field": "attrs__const_type",
                "label": {"en": "Construction Type"},
                "type": "string",
                "input": "checkbox",
                "optgroup": "attributes",
                "values": [
                    "attic",
                    "single-storey",
                    "staggered-level",
                    "modular prefab",
                    "full-storey",
                ],
                "operators": ["in", "not_in"],
            },
            {
                "id": "attrs__owner_date",
                "field": "attrs__owner_date",
                "label": {"en": "Owner Date"},
                "type": "date",
                "plugin": "datepicker",
                "plugin_config": {
                    "format": "yyyy-mm-dd",
                    "todayBtn": "linked",
                    "todayHighlight": True,
                    "autoclose": True,
                },
                "optgroup": "attributes",
            },
            {
                "id": "attrs__owner_type",
                "field": "attrs__owner_type",
                "label": {"en": "Owner Type"},
                "type": "string",
                "input": "checkbox",
                "values": ["moral", "physical"],
                "operators": ["in", "not_in"],
                "optgroup": "attributes",
            },
            {
                "id": "attrs__owner_status",
                "field": "attrs__owner_status",
                "label": {"en": "Owner Status"},
                "type": "string",
                "input": "checkbox",
                "values": [
                    "undivided co-owner",
                    "lessor of public land",
                    "landowner",
                    "condo owner",
                    "other",
                    "tenant of tax-exempt building",
                    "lessor",
                    "building owner on public land",
                    "trailer building owner",
                ],
                "operators": ["in", "not_in"],
                "optgroup": "attributes",
            },
            {
                "id": "attrs__lot_lin_dim",
                "field": "attrs__lot_lin_dim",
                "label": {"en": "Lot Linear Dimension"},
                "optgroup": "attributes",
                "type": "double",
                "input": "number",
                "validation": {"min": 0, "step": 0.01},
            },
            {
                "id": "attrs__lot_area",
                "field": "attrs__lot_area",
                "label": {"en": "Lot Area"},
                "optgroup": "attributes",
                "type": "double",
                "input": "number",
                "validation": {"min": 0, "step": 0.01},
            },
            {
                "id": "attrs__apprais_date",
                "field": "attrs__apprais_date",
                "label": {"en": "Appraisal Date"},
                "optgroup": "attributes",
                "type": "date",
                "plugin": "datepicker",
                "plugin_config": {
                    "format": "yyyy-mm-dd",
                    "todayBtn": "linked",
                    "todayHighlight": True,
                    "autoclose": True,
                },
            },
            {
                "id": "attrs__lot_value",
                "field": "attrs__lot_value",
                "label": {"en": "Lot Value"},
                "optgroup": "attributes",
                "type": "double",
                "input": "number",
                "validation": {"min": 0, "step": 0.01},
            },
            {
                "id": "attrs__building_value",
                "field": "attrs__building_value",
                "label": {"en": "Building Value"},
                "optgroup": "attributes",
                "type": "double",
                "input": "number",
                "validation": {"min": 0, "step": 0.01},
            },
            {
                "id": "attrs__value",
                "field": "attrs__value",
                "label": {"en": "Value"},
                "optgroup": "attributes",
                "type": "double",
                "input": "number",
                "validation": {"min": 0, "step": 0.01},
            },
            {
                "id": "attrs__prev_value",
                "field": "attrs__prev_value",
                "label": {"en": "Previous Value"},
                "optgroup": "attributes",
                "type": "double",
                "input": "number",
                "validation": {"min": 0, "step": 0.01},
            },
        ],
    )
    dataset.save()



    for offset in tqdm(
        range(0, num_units, chunk_length),
        desc="Upsert Buildings from EvalUnits",
    ):
        try:
            from_cur.execute(
                f"""SELECT 
                    e.id as id, e.lat as lat, e.lng as lng, e.point as point, 
                    e.address as address, 
                    e.street_name as street_name, 
                    concat(e.num_adr_inf, e.num_adr_inf_2, e.num_adr_sup, e.num_adr_sup_2) as street_num, 
                    e.muni as muni, 
                    e.arrond as submuni,
                    e.num_dwelling as num_dwellings, 
                    e.max_floors as num_floors, 
                    e.floor_area as floor_area, 
                    e.const_yr as const_yr,
                    e.phys_link as phys_link, 
                    e.const_type as const_type, 
                    e.owner_date as owner_date, 
                    e.owner_type as owner_type, 
                    e.owner_status as owner_status, 
                    e.lot_lin_dim as lot_lin_dim, 
                    e.lot_area as lot_area, 
                    e.apprais_date as apprais_date, 
                    e.lot_value as lot_value, 
                    e.building_value as building_value, 
                    e.value as value, 
                    e.prev_value as prev_value,
                    v.p_bldg as p_bldg,
                    v.p_metal as p_metal
                FROM {EVALUNITS_TABLE} e
                INNER JOIN vqa_results v ON
                    e.id = v.id
                WHERE v.p_bldg > 0.5 and v.p_metal > 0.5
                ORDER BY e.id DESC
                LIMIT {chunk_length} offset {offset}
            """
            )
            unit_batch = from_cur.fetchall()

            buildings_to_write = []

            # Convert to new model
            for unit in unit_batch:

                attrs = {
                    "p_metal": float(unit["p_metal"]),
                    "p_bldg": float(unit["p_bldg"]),
                    "phys_link": unit["phys_link"],
                    "const_type": unit["const_type"],
                    "owner_date": unit["owner_date"].strftime("%Y-%m-%d"),
                    "owner_type": unit["owner_type"],
                    "owner_status": unit["owner_status"],
                    "lot_lin_dim": unit["lot_lin_dim"],
                    "lot_area": unit["lot_area"],
                    "apprais_date": unit["apprais_date"].strftime("%Y-%m-%d"),
                    "lot_value": unit["lot_value"],
                    "building_value": unit["building_value"],
                    "value": unit["value"],
                    "prev_value": unit["prev_value"],
                }

                new_model = {
                    "ext_id": unit["id"],
                    "lat": unit["lat"],
                    "lng": unit["lng"],
                    "point": unit["point"],
                    "address": unit["address"],
                    "street_name": unit["street_name"],
                    "street_num": unit["street_num"],
                    "muni": unit["muni"],
                    "submuni": unit["submuni"],
                    "const_year": unit["const_yr"],
                    "num_floors": unit["num_floors"],
                    "floor_area": unit["floor_area"],
                    "attrs": attrs,
                    "dataset": dataset,
                }

                buildings_to_write.append(Building(**new_model))

            Building.objects.bulk_create(
                buildings_to_write,
                update_conflicts=True,
                unique_fields=["ext_id", "lat", "lng", "address", "muni"],
                update_fields=[
                    "ext_id",
                    "lat",
                    "lng",
                    "point",
                    "address",
                    "street_name",
                    "street_num",
                    "muni",
                    "submuni",
                    "postal_code",
                    "const_year",
                    "num_floors",
                    "floor_area",
                    "attrs",
                    "dataset",
                ],
            )
            if not dry_run:
                from_db.commit()

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
        upsert_evalunits(dry_run=options["dry_run"])
