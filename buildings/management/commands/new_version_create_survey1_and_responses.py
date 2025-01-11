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
        user="bitdbuser",
        password="password",
        host="127.0.0.1",
        port=5433,
        database="bitdb",
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
        # Frank
        created_by=SYSTEM_USER,
        dataset=dataset,
        schema={
            "appendages": {
                "type": "text",
                "label": {"en": "Appendages"},
                "widget": "multi_checkbox_specify",
                "options": {
                    "other": {"option_text": {"en": "Other (specify)"}},
                    "balconies": {"option_text": {"en": "Balconies"}},
                    "vestibules": {"option_text": {"en": "Exterior Vestibules"}},
                    "canopies_eaves": {"option_text": {"en": "Roof overhangs/eaves"}},
                    "porches_stoops": {"option_text": {"en": "Porches/stoops"}},
                },
                "has_modal": True,
                "question_text": {
                    "en": "Select any and all significant appendages to the building faces."
                },
                "widget_config": {
                    "attrs": {"class": "survey-1col"},
                    "specify_input_type": "text",
                    "specify_option_value": "other",
                },
                "question_number": 7,
            },
            "num_storeys": {
                "type": "integer",
                "label": {"en": "Number of Storeys"},
                "widget": "radio_w_specify",
                "options": {
                    "": {"option_text": {"en": "Unsure"}},
                    "num_storeys": {"option_text": {"en": "Number of storeys:"}},
                },
                "has_modal": True,
                "question_text": {
                    "en": "How many storeys above-ground does the building have?"
                },
                "widget_config": {
                    "attrs": {"class": "survey-1col"},
                    "specify_input_type": "number",
                    "specify_option_value": "num_storeys",
                },
                "question_number": 4,
            },
            "has_basement": {
                "type": "boolean",
                "label": {"en": "Has Basement"},
                "widget": "radio",
                "options": {
                    True: {"option_text": {"en": "Yes"}},
                    False: {"option_text": {"en": "No"}},
                    None: {"option_text": {"en": "Unsure"}},
                },
                "has_modal": True,
                "question_text": {"en": "Does the building appear to have a basement?"},
                "widget_config": {"attrs": {"class": "survey-1col"}},
                "question_number": 5,
            },
            "roof_geometry": {
                "type": "text",
                "label": {"en": "Roof Geometry"},
                "widget": "multi_checkbox_required",
                "options": {
                    "flat": {"option_text": {"en": "Flat"}},
                    "curved": {"option_text": {"en": "Curved"}},
                    "unsure": {"option_text": {"en": "Unsure"}},
                    "complex": {"option_text": {"en": "Complex"}},
                    "pitch_low": {"option_text": {"en": "Low Pitched"}},
                    "pitch_high": {"option_text": {"en": "High Pitched"}},
                },
                "has_modal": True,
                "question_text": {"en": "Select all that describes the roof geometry."},
                "widget_config": {"attrs": {"class": "survey-3col"}},
                "question_number": 12,
            },
            "facade_condition": {
                "type": "boolean",
                "label": {"en": "Facade Condition"},
                "widget": "radio",
                "options": {
                    True: {"option_text": {"en": "Yes"}},
                    False: {"option_text": {"en": "No"}},
                    None: {"option_text": {"en": "Unsure"}},
                },
                "has_modal": True,
                "question_text": {
                    "en": "Are the façades in poor condition and in need of replacement?"
                },
                "widget_config": {"attrs": {"class": "survey-1col"}},
                "question_number": 9,
            },
            "new_or_renovated": {
                "type": "text",
                "label": {"en": "New or Renovated"},
                "widget": "multi_checkbox",
                "options": {
                    "newly_built": {"option_text": {"en": "Newly built"}},
                    "recently_renovated": {"option_text": {"en": "Recently renovated"}},
                },
                "has_modal": True,
                "question_text": {
                    "en": "Does the building look newly built or recently renovated?"
                },
                "question_number": 13,
            },
            "exterior_cladding": {
                "type": "text",
                "label": {"en": "Exterior Cladding"},
                "widget": "multi_checkbox_required_specify",
                "options": {
                    "wood": {"option_text": {"en": "Wood"}},
                    "metal": {"option_text": {"en": "Metal"}},
                    "other": {"option_text": {"en": "Other (Specify)"}},
                    "vinyl": {"option_text": {"en": "Vinyl"}},
                    "unsure": {"option_text": {"en": "Unsure"}},
                    "plaster": {"option_text": {"en": "Plaster"}},
                    "concrete": {"option_text": {"en": "Concrete"}},
                    "curtain_wall": {"option_text": {"en": "Curtain Wall"}},
                    "brick_masonry": {"option_text": {"en": "Brick Masonry"}},
                    "stone_masonry": {"option_text": {"en": "Stone Masonry"}},
                },
                "has_modal": True,
                "question_text": {
                    "en": "Select all widgets of exterior cladding does the building appear to have."
                },
                "widget_config": {
                    "attrs": {"class": "survey-3col"},
                    "specify_input_type": "text",
                    "specify_option_value": "other",
                },
                "question_number": 8,
            },
            "has_simple_volume": {
                "type": "boolean",
                "label": {"en": "Simple Volume"},
                "widget": "radio",
                "options": {
                    True: {"option_text": {"en": "Yes"}},
                    False: {"option_text": {"en": "No"}},
                },
                "has_modal": True,
                "question_text": {
                    "en": "Does the building have a simple volumetric form?"
                },
                "question_number": 3,
            },
            "site_obstructions": {
                "type": "text",
                "label": {"en": "Site Obstructions"},
                "widget": "multi_checkbox_specify",
                "options": {
                    "buildings": {"option_text": {"en": "Buildings"}},
                    "overhead_wires": {
                        "option_text": {
                            "en": "Overhead wires, incl. those blocking general access to site"
                        }
                    },
                    "trees_or_landscaping": {
                        "option_text": {"en": "Important trees or landscaping"}
                    },
                    "other": {"option_text": {"en": "Other (Specify)"}},
                },
                "has_modal": True,
                "question_text": {
                    "en": "Select any and all obstructions to machine access around the building."
                },
                "question_number": 6,
            },
            "window_wall_ratio": {
                "type": "boolean",
                "label": {"en": "Window-to-Wall Ratio"},
                "widget": "radio",
                "options": {
                    True: {"option_text": {"en": "Yes"}},
                    False: {"option_text": {"en": "No"}},
                    None: {"option_text": {"en": "Unsure"}},
                },
                "has_modal": True,
                "question_text": {
                    "en": "Does glazing make up more than 40% of the total visible façade area?"
                },
                "widget_config": {"attrs": {"class": "survey-1col"}},
                "question_number": 10,
            },
            "has_simple_footprint": {
                "type": "boolean",
                "label": {"en": "Simple Footprint"},
                "widget": "radio",
                "options": {
                    True: {"option_text": {"en": "Yes"}},
                    False: {"option_text": {"en": "No"}},
                },
                "has_modal": True,
                "question_text": {"en": "Does the building have a simple footprint?"},
                "question_number": 2,
            },
            "self_similar_cluster": {
                "type": "integer",
                "label": {"en": "Self Similar Cluster"},
                "widget": "radio_w_specify",
                "options": {
                    "": {"option_text": {"en": "No"}},
                    "num_buildings_in_cluster": {
                        "option_text": {"en": "Buildings in cluster:"}
                    },
                },
                "has_modal": True,
                "question_text": {
                    "en": "Is the building part of a self-similar cluster? If so, how many buildings are in the cluster?"
                },
                "widget_config": {
                    "specify_input_type": "number",
                    "specify_option_value": "num_buildings_in_cluster",
                },
                "question_number": 1,
            },
            "large_irregular_windows": {
                "type": "text",
                "label": {"en": "Large/Irregular Windows"},
                "widget": "multi_checkbox",
                "options": {
                    "irregular_windows": {"option_text": {"en": "Irregularly shaped"}},
                    "very_large_windows": {"option_text": {"en": "Very large"}},
                },
                "has_modal": True,
                "question_text": {
                    "en": "Are there very large and/or irregularly shaped windows?"
                },
                "widget_config": {"attrs": {"class": "survey-1col"}},
                "question_number": 11,
            },
        },
    )
    survey.save()

    print("Create survey1 and migrate responses")

    for offset in tqdm(range(0, num_units, chunk_length)):
        try:
            from_cur.execute(
                f"""select
                        s.*,
                        v.user_id as user_id,
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
                    "site_obstructions": resp["site_obstructions"],
                    "appendages": resp["appendages"],
                    "exterior_cladding": resp["exterior_cladding"],
                    "facade_condition": resp["facade_condition"],
                    "window_wall_ratio": resp["window_wall_ratio"],
                    "large_irregular_windows": resp["large_irregular_windows"],
                    "roof_geometry": resp["roof_geometry"],
                    "new_or_renovated": resp["new_or_renovated"],
                }

                responses_to_write.append(
                    Response(
                        data=data,
                        building=Building.objects.get(pk=resp["building_id"]),
                        survey=survey,
                        created_by=User.objects.get(pk=resp["user_id"]),
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
