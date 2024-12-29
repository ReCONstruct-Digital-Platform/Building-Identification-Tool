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

    survey, _ = Survey.objects.get_or_create(
        name="Recon Survey V1",
        description="Reconstruct's initial survey to find good deep energy retrofit candidates among HLMs",
        # Frank
        created_by=User.objects.get(pk=32),
        dataset=Dataset.objects.get(pk=2),
        schema={
            "self_similar_cluster": {
                "label": "Self Similar Cluster",
                "widget": "radio_specify_integer",
                "question_text": {
                    "en": "Is the building part of a self-similar cluster? If so, how many buildings are in the cluster?"
                },
            },
            "has_simple_footprint": {
                "label": "Simple Footprint",
                "widget": "boolean",
                "question_text": {"en": "Does the building have a simple footprint?"},
            },
            "has_simple_volume": {
                "label": "Simple Volume",
                "widget": "boolean",
                "question_text": {
                    "en": "Does the building have a simple volumetric form?"
                },
            },
            "num_storeys": {
                "label": "Num. Storeys",
                "widget": "integer",
                "question_text": {
                    "en": "How many storeys above-ground does the building have?"
                },
            },
            "has_basement": {
                "label": "Has Basement",
                "widget": "boolean",
                "question_text": {"en": "Does the building appear to have a basement?"},
            },
            "site_obstructions": {
                "label": "Site Obstructions",
                "widget": "multi_checkbox_specify",
                "question_text": {
                    "en": "Select any and all obstructions to machine access around the building."
                },
                "values": {
                    "trees_or_landscaping": {
                        "question_text": {"en": "Important trees or landscaping"}
                    },
                    "buildings": {"question_text": {"en": "Buildings"}},
                    "overhead_wires": {
                        "question_text": {
                            "en": "Overhead wires, incl. those blocking general access to site"
                        }
                    },
                },
            },
            "appendages": {
                "label": "Appendages",
                "widget": "multi_checkbox_specify",
                "question_text": {
                    "en": "Select any and all significant appendages to the building faces."
                },
                "values": {
                    "canopies_eaves": {"question_text": {"en": "Roof overhangs/eaves"}},
                    "balconies": {"question_text": {"en": "Balconies"}},
                    "porches_stoops": {"question_text": {"en": "Porches/stoops"}},
                    "vestibules": {"question_text": {"en": "Exterior Vestibules"}},
                },
            },
            "exterior_cladding": {
                "label": "Exterior Cladding",
                "widget": "multi_checkbox_specify_required",
                "question_text": {
                    "en": "Select all widgets of exterior cladding does the building appear to have."
                },
                "values": {
                    "brick_masonry": {"question_text": {"en": "Brick Masonry"}},
                    "concrete": {"question_text": {"en": "Concrete"}},
                    "curtain_wall": {"question_text": {"en": "Curtain Wall"}},
                    "plaster": {"question_text": {"en": "Plaster"}},
                    "metal": {"question_text": {"en": "Metal"}},
                    "vinyl": {"question_text": {"en": "Vinyl"}},
                    "stone_masonry": {"question_text": {"en": "Stone Masonry"}},
                    "wood": {"question_text": {"en": "Wood"}},
                    "unsure": {"question_text": {"en": "Unsure"}},
                },
            },
            "facade_condition": {
                "label": "Facade Condition",
                "widget": "boolean",
                "question_text": {
                    "en": "Are the façades in poor condition and in need of replacement?"
                },
            },
            "window_wall_ratio": {
                "label": "Window-to-Wall Ratio",
                "widget": "boolean",
                "question_text": {
                    "en": "Does glazing make up more than 40% of the total visible façade area?"
                },
            },
            "large_irregular_windows": {
                "label": "Large/Irregular Windows",
                "widget": "boolean",
                "question_text": {
                    "en": "Are there very large and/or irregularly shaped windows?"
                },
            },
            "roof_geometry": {
                "label": "Roof Geometry",
                "widget": "multi_checkbox_specify_required",
                "question_text": {"en": "Select all that describes the roof geometry?"},
                "values": {
                    "flat": {"question_text": {"en": "Flat"}},
                    "pitch_low": {"question_text": {"en": "Low Pitched"}},
                    "pitch_high": {"question_text": {"en": "High Pitched"}},
                    "curved": {"question_text": {"en": "Curved"}},
                    "complex": {"question_text": {"en": "Complex"}},
                    "unsure": {"question_text": {"en": "Unsure"}},
                },
            },
            "new_or_renovated": {
                "label": "New or Renovated",
                "widget": "multi_checkbox_specify",
                "question_text": {
                    "en": "Does the building look newly built or recently renovated?"
                },
                "values": {
                    "newly_built": {"question_text": {"en": "Newly built"}},
                    "recently_renovated": {
                        "question_text": {"en": "Recently renovated"}
                    },
                },
            },
        },
    )
    survey.save()

    for offset in tqdm(
        range(0, num_units, chunk_length),
        desc="Create New model Responses from old Votes",
    ):
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

                responses_to_write.append(Response(
                    data = data,
                    building = Building.objects.get(pk=resp["building_id"]),
                    survey = survey,
                    created_by = User.objects.get(pk=resp["user_id"])
                ))

            Response.objects.bulk_create(
                responses_to_write,
                update_conflicts=True,
                unique_fields=["building", "survey", "created_by"],
                update_fields=[
                    "data"
                ],
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
