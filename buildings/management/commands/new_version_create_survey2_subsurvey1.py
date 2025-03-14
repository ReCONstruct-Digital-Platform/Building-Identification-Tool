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
    transform_all_values,
)
from buildings.models.models import User
from buildings.models.newmodels import Building, Dataset, Response, Survey
from buildings.models.surveys import (
    APPENDAGES,
    FACADE_MATERIALS,
    NEW_OR_RENOVATED,
    ROOF_GEOMETRIES,
    SITE_OBSTRUCTIONS,
    WINDOWS,
)

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
        schema={
            "appendages": {
                "pos": 7,
                "type": "text",
                "label": {"en": "Appendages"},
                "widget": "multi_checkbox_specify",
                "options": [
                    {"pos": 0, "val": "Balconies", "label": {"en": "Balconies"}},
                    {
                        "pos": 1,
                        "val": "Exterior Vestibules",
                        "label": {"en": "Exterior Vestibules"},
                    },
                    {
                        "pos": 2,
                        "val": "Roof overhangs/eaves",
                        "label": {"en": "Roof overhangs/eaves"},
                    },
                    {
                        "pos": 3,
                        "val": "Porches/stoops",
                        "label": {"en": "Porches/stoops"},
                    },
                    {
                        "pos": 4,
                        "val": "No obstructions",
                        "label": {"en": "No obstructions"},
                    },
                    {
                        "pos": 5,
                        "val": "Other (specify)",
                        "label": {"en": "Other (specify)"},
                    },
                ],
                "question_text": {
                    "en": "Select any and all significant appendages to the building faces."
                },
                "widget_config": {
                    "attrs": {"class": "survey-1col"},
                    "specify_input_type": "text",
                    "specify_option_value": "other",
                },
            },
            "num_storeys": {
                "pos": 4,
                "type": "integer",
                "label": {"en": "Number of Storeys"},
                "widget": "radio_w_specify",
                "options": [
                    {
                        "pos": 0,
                        "val": "Number of storeys",
                        "label": {"en": "Number of storeys"},
                    },
                    {"pos": 1, "val": None, "label": {"en": "Unsure"}},
                ],
                "question_text": {
                    "en": "How many storeys above-ground does the building have?"
                },
                "widget_config": {
                    "attrs": {"class": "survey-1col"},
                    "specify_input_type": "number",
                    "specify_option_value": "num_storeys",
                },
            },
            "has_basement": {
                "pos": 5,
                "type": "boolean_or_null",
                "label": {"en": "Has Basement"},
                "widget": "radio",
                "options": [
                    {"pos": 0, "val": True, "label": {"en": "Yes"}},
                    {"pos": 1, "val": False, "label": {"en": "No"}},
                    {"pos": 2, "val": None, "label": {"en": "Unsure"}},
                ],
                "question_text": {"en": "Does the building appear to have a basement?"},
                "widget_config": {"attrs": {"class": "survey-1col"}},
            },
            "roof_geometry": {
                "pos": 12,
                "type": "text",
                "label": {"en": "Roof Geometry"},
                "widget": "multi_checkbox",
                "options": [
                    {"pos": 0, "val": "Flat", "label": {"en": "Flat"}},
                    {"pos": 1, "val": "Curved", "label": {"en": "Curved"}},
                    {"pos": 2, "val": "Unsure", "label": {"en": "Unsure"}},
                    {"pos": 3, "val": "Complex", "label": {"en": "Complex"}},
                    {"pos": 4, "val": "Low Pitched", "label": {"en": "Low Pitched"}},
                    {"pos": 5, "val": "High Pitched", "label": {"en": "High Pitched"}},
                ],
                "question_text": {"en": "Select all that describes the roof geometry."},
                "widget_config": {
                    "is_required": True,
                    "attrs": {"class": "survey-3col"},
                },
            },
            "facade_condition": {
                "pos": 9,
                "type": "boolean_or_null",
                "label": {"en": "Facade Condition"},
                "widget": "radio",
                "options": [
                    {"pos": 0, "val": True, "label": {"en": "Yes"}},
                    {"pos": 1, "val": False, "label": {"en": "No"}},
                    {"pos": 2, "val": None, "label": {"en": "Unsure"}},
                ],
                "question_text": {
                    "en": "Are the façades in poor condition and in need of replacement?"
                },
                "widget_config": {"attrs": {"class": "survey-1col"}},
            },
            "new_or_renovated": {
                "pos": 13,
                "type": "text",
                "label": {"en": "New or Renovated"},
                "widget": "multi_checkbox",
                "options": [
                    {"pos": 0, "val": "Newly built", "label": {"en": "Newly built"}},
                    {
                        "pos": 1,
                        "val": "Recently renovated",
                        "label": {"en": "Recently renovated"},
                    },
                ],
                "question_text": {
                    "en": "Does the building look newly built or recently renovated?"
                },
            },
            "exterior_cladding": {
                "pos": 8,
                "type": "text",
                "label": {"en": "Exterior Cladding"},
                "widget": "multi_checkbox_specify",
                "options": [
                    {"pos": 0, "val": "Wood", "label": {"en": "Wood"}},
                    {"pos": 1, "val": "Metal", "label": {"en": "Metal"}},
                    {"pos": 2, "val": "Vinyl", "label": {"en": "Vinyl"}},
                    {"pos": 3, "val": "Plaster", "label": {"en": "Plaster"}},
                    {"pos": 4, "val": "Concrete", "label": {"en": "Concrete"}},
                    {"pos": 5, "val": "Curtain Wall", "label": {"en": "Curtain Wall"}},
                    {
                        "pos": 6,
                        "val": "Brick Masonry",
                        "label": {"en": "Brick Masonry"},
                    },
                    {
                        "pos": 7,
                        "val": "Stone Masonry",
                        "label": {"en": "Stone Masonry"},
                    },
                    {"pos": 8, "val": "Unsure", "label": {"en": "Unsure"}},
                    {"pos": 9, "val": "Other", "label": {"en": "Other (Specify)"}},
                ],
                "question_text": {
                    "en": "Select all types of exterior cladding does the building appear to have."
                },
                "widget_config": {
                    "attrs": {"class": "survey-3col"},
                    "is_required": True,
                    "specify_input_type": "text",
                    "specify_option_value": "Other",
                },
            },
            "has_simple_volume": {
                "pos": 3,
                "type": "boolean",
                "label": {"en": "Simple Volume"},
                "widget": "radio",
                "options": [
                    {"pos": 0, "val": True, "label": {"en": "Yes"}},
                    {"pos": 1, "val": False, "label": {"en": "No"}},
                ],
                "question_text": {
                    "en": "Does the building have a simple volumetric form?"
                },
            },
            "site_obstructions": {
                "pos": 6,
                "type": "text",
                "label": {"en": "Site Obstructions"},
                "widget": "multi_checkbox_specify",
                "options": [
                    {
                        "pos": 0,
                        "val": "Important trees or landscaping",
                        "label": {"en": "Important trees or landscaping"},
                    },
                    {"pos": 1, "val": "Buildings", "label": {"en": "Buildings"}},
                    {
                        "pos": 2,
                        "val": "Overhead wires",
                        "label": {"en": "Overhead wires"},
                    },
                    {
                        "pos": 3,
                        "val": "No obstructions",
                        "label": {"en": "No obstructions"},
                    },
                    {
                        "pos": 4,
                        "val": "Other (Specify)",
                        "label": {"en": "Other (Specify)"},
                    },
                ],
                "question_text": {
                    "en": "Select any and all obstructions to machine access around the building."
                },
            },
            "window_wall_ratio": {
                "pos": 10,
                "type": "boolean_or_null",
                "label": {"en": "Window-to-Wall Ratio"},
                "widget": "radio",
                "options": [
                    {"pos": 0, "val": True, "label": {"en": "Yes"}},
                    {"pos": 1, "val": False, "label": {"en": "No"}},
                    {"pos": 2, "val": None, "label": {"en": "Unsure"}},
                ],
                "question_text": {
                    "en": "Does glazing make up more than 40% of the total visible façade area?"
                },
                "widget_config": {"attrs": {"class": "survey-1col"}},
            },
            "has_simple_footprint": {
                "pos": 2,
                "type": "boolean",
                "label": {"en": "Simple Footprint"},
                "widget": "radio",
                "options": [
                    {"pos": 0, "val": True, "label": {"en": "Yes"}},
                    {"pos": 1, "val": False, "label": {"en": "No"}},
                ],
                "question_text": {"en": "Does the building have a simple footprint?"},
            },
            "self_similar_cluster": {
                "pos": 1,
                "type": "integer",
                "label": {"en": "Self Similar Cluster"},
                "widget": "radio_w_specify",
                "options": [
                    {
                        "pos": 0,
                        "val": "Buildings in cluster",
                        "label": {"en": "Buildings in cluster"},
                    },
                    {"pos": 1, "val": None, "label": {"en": "No"}},
                ],
                "question_text": {
                    "en": "Is the building part of a self-similar cluster? If so, how many buildings are in the cluster?"
                },
                "widget_config": {
                    "specify_input_type": "number",
                    "specify_option_value": "Buildings in cluster",
                },
            },
            "large_irregular_windows": {
                "pos": 11,
                "type": "text",
                "label": {"en": "Large/Irregular Windows"},
                "widget": "multi_checkbox",
                "options": [
                    {
                        "pos": 1,
                        "val": "Irregularly shaped",
                        "label": {"en": "Irregularly shaped"},
                    },
                    {
                        "pos": 0,
                        "val": "Very large",
                        "label": {"en": "Very large"},
                    },
                ],
                "question_text": {
                    "en": "Are there very large and/or irregularly shaped windows?"
                },
                "widget_config": {"attrs": {"class": "survey-1col"}},
            },
        },
        modals={
            "self_similar_cluster": {
                "title": "Self-Similar Clusters",
                "body": """<div>
            <div class="infobox-section">
              <em>Definition:</em>
              <p class="infobox-p">
                A building is part of a <strong>self-similar cluster</strong> if it close to other buildings built at the
                same time, following the same construction methods, and using the same materials.
                Most of the time, they will seem virtually identical copies.
              </p>
            </div>
            <div class="infobox-section">
              <em>Relevance:</em>
              <p class="infobox-p">
                This is important for the value case of retrofits, as a multi-building project has economies of scale
                which makes retrofitting a cluster more attractive than retrofitting a single building.
              </p>
            </div>
            <div class="infobox-section">
              <em>Note:</em>
              <p class="infobox-p">
                Presence of the <span class="badge text-bg-info">Multiple Addresses</span> tag makes this more likely
                as the evaluation unit could contain multiple buildings.
              </p>
            </div>
            <div class="infobox-section">
              <strong>Example 1:</strong>
              <p class="infobox-p">
                We can see from the streetview that there is an almost identical building to the right.
                The satellite view gives a bigger picture where wee see that there seems to be a 5 building cluster.
              </p>
              <img class="infobox-img img-fluid" src="/static/images/survey_info/q1_cluster/selfsimilar_sv.jpg" alt="A streetview of a building part of a self-similar cluster" loading="lazy">
              <img class="infobox-img img-fluid" src="/static/images/survey_info/q1_cluster/selfsimilar_sat.jpg" alt="A satellite view of a building part of a self-similar cluster" loading="lazy">
            </div>
  
            <div class="infobox-section">
              <strong>
                Example 2:
              </strong>
              <p class="infobox-p">
                Again, it is clear from the streetview image that there are multiple similar buildings.
                The satellite view shows a cluster of 4 (or 8) buildings.
              </p>
              <img class="infobox-img img-fluid" src="/static/images/survey_info/q1_cluster/selfsimilar_sv_2.jpg" alt="Another streetview of a building part of a self-similar cluster" loading="lazy">
              <img class="infobox-img img-fluid" src="/static/images/survey_info/q1_cluster/selfsimilar_sat_2.jpg" alt="Another satellite view of a building part of a self-similar cluster" loading="lazy">
            </div>
          </div>""",
            },
            "has_simple_footprint": {
                "title": "Building Footprint",
                "body": """<div>
            <div class="infobox-section">
              <em>Definition:</em>
              <p class="infobox-p">
                A building has a <strong>simple footprint</strong> if its intersection with the ground is 
                through one or two simple geometric shapes (one or two rectangles). A complex footprint can 
                have many corners, irregular angles, or multiple shapes of different types.  
              </p>
            </div>
            <div class="infobox-section">
              <em>Note:</em>
              <p class="infobox-p">
                This is usually more readily visible from the satellite view of the building.
              </p>
            </div>
          </div>""",
            },
            "has_simple_volume": {
                "title": "Volumetric Shape",
                "body": """<div>
              <div class="infobox-section">
                <em>Definition:</em>
              <p class="infobox-p">
                A <strong>simple volumetric form</strong> is a rectangular volume or a combination of a few rectangular 
                volumes. A complex volumetric form can be any irregular volumes, often consisting of free-flowing 
                curves, or of many rectangular volumes creating many angles. 
              </p>
            </div>
          </div>""",
            },
            "num_storeys": {
                "title": "Number of Storeys",
                "body": """<div>
            <div class="infobox-section">
              <em>Definition:</em>
              <p class="infobox-p">
                Any storey (floor) above the surface of the ground is a storey above-ground.
                The basement is not considered a storey.
              </p>  
            </div>
          </div> """,
            },
            "has_basement": {
                "title": "Basement",
                "body": """<div>
              <div class="infobox-section">
                <em>Definition:</em>
                <p class="infobox-p">
                  Any floor partly or entirely submerged in the ground is a basement. A building is likely to have 
                  a basement if there are windows between the ground level and the first floor. 
                </p>
                <img class="infobox-img img-fluid" loading="lazy" src="/static/images/survey_info/q5_basement/q5_basement.jpg">  
              </div>
            </div>""",
            },
            "site_obstructions": {
                "title": "Site Obstructions",
                "body": """            <div>

              <div>
                <div class="infobox-section">
                  <em>Definition:</em>
                  <p class="infobox-p">
                    Please select any <strong>potential barriers</strong> that would hinder a crane's access to the 
                    building façade, such as: power lines or very large/old trees within 3m of the building, 
                    or another building less than 3m away. 
                  </p>
                </div>
              </div>
              <div class="infobox-section">
                <em>Relevance:</em>
                <p class="infobox-p">
                  Common retrofit approaches include installing panel solutions by crane, therefore obstructions 
                  may create challenges in the installation process and even make a panelized retrofit infeasible.
                </p>
              </div>
              <div class="infobox-section">
                <strong>
                  Example (Building):
                </strong>
                <p class="infobox-p">
                  This building has another building less than 3m away and it seems like a large vehicle would have trouble getting around.
                  <img class="infobox-img img-fluid" src="/static/images/survey_info/q6_obstructions/q6_building.jpg" loading="lazy">
                </p>
              </div>
              <div class="infobox-section">
                <strong>
                  Example (Wires):
                </strong>
                <p class="infobox-p">
                  These two building have wires that would need to be disconnected to do a panelized retrofit.
                  <img class="infobox-img img-fluid" src="/static/images/survey_info/q6_obstructions/q6_building_wire.jpg" loading="lazy">
                  <img class="infobox-img img-fluid" src="/static/images/survey_info/q6_obstructions/q6_building_wire_2.jpg" loading="lazy">
                </p>
              </div>
              <div class="infobox-section">
                <strong>
                  Example (Trees):
                </strong>
                <p class="infobox-p">
                  This building has large trees very close to the facade.
                  <img class="infobox-img img-fluid" src="/static/images/survey_info/q6_obstructions/q6_tree.jpg" loading="lazy">
                </p>
              </div>
              <div class="infobox-section">
                <strong>
                  Example (Not obstructions):
                </strong>
                <p class="infobox-p">
                  These buildings have wires or trees around but reasonably far away for machinery to access the facade.
                  <img class="infobox-img img-fluid" src="/static/images/survey_info/q6_obstructions/q6_tree_ok.jpg" loading="lazy">
                  <img class="infobox-img img-fluid" src="/static/images/survey_info/q6_obstructions/q6_wire_ok.jpg" loading="lazy">
                </p>
              </div>
            </div>""",
            },
            "appendages": {
                "title": "Appendages",
                "body": """<div>
              <div class="infobox-section">
                <em>Definition:</em>
                <p class="infobox-p">
                  <strong>Appendages</strong> are any noticeable extruding features on the building including: balconies, large roof overhangs, 
                  or decorative protrusions.
                </p>
              </div>
              <div class="infobox-section">
                <em>Relevance:</em>
                <p class="infobox-p">
                  Appendages increase the complexity of doing panelized retrofits, as they will have to be removed in most cases.
                  Regarding balconies, they are often a major cause of 
                  <a href="https://passipedia.org/basics/building_physics_-_basics/thermal_bridges/thermal_bridge_definition">
                    thermal bridging </a> which leads to heat loss and energy inefficiency.
                </p>
              </div>
              <div lass="infobox-section">
                <em>Note:</em>
                <p class="infobox-p">
                  Considering most people are attached to their balconies and they have to be removed for panelized retrofits, they
                  could be a source of conflict and work against the project starting. Balconies can always be added back over the panels,
                  but at a higher project cost.
                </p>
              </div>
              <div class="infobox-section mt-1">
                <strong>Example:</strong>
                <p class="infobox-p">
                  The following building has a lot of appendages, including balconies, eaves, porches.
                </p>
                <img class="infobox-img img-fluid" loading="lazy" src="/static/images/survey_info/q7_appendages/weird_appendages.png">  
              </div>
            </div>""",
            },
            "exterior_cladding": {
                "title": "Exterior Cladding",
                "body": """<div>
              <div class="infobox-section">
                <em>Definition:</em>
                <img class="infobox-img img-fluid" loading="lazy" src="/static/images/survey_info/q8_cladding/q8_cladding.jpg  ">  
              </div>
              <div class="infobox-section">
                <em>Relevance:</em>
                <p class="infobox-p">
                  Panelized retrofit strategies need to consider the existing wall composition and 
                  materials because some materials are more able to support panelized solutions than others. 
                </p>
              </div>
            </div>""",
            },
            "facade_condition": {
                "title": "Façade Condition",
                "body": """<div>
              <div class="infobox-section">
                <em>Definition:</em>
                <p class="infobox-p">
                  A façade in poor condition may include: cladding material in poor shape with multiple areas 
                  displaying mold infestation and/or rot, noticeable water stains that can be identified at first 
                  glance, or if the overall condition of the exterior façade appears to be due for renovation. 
                </p>
              </div>
              <div class="infobox-section">
                <em>Relevance:</em>
                <p class="infobox-p">
                  Buildings with façades in poor condition are already in need of renovation at which point a 
                  panelized retrofit can be done at little extra cost, and provide additional benefits. We call these 
                  "anyway" retrofits.
                </p>
              </div>
            </div>""",
            },
            "window_wall_ratio": {
                "title": "Glazing Ratio",
                "body": """<div>
              <div class="infobox-section">
                <p class="infobox-p">
                  The following diagram illustrates proportions of glazing (fenestration) relative to the façade area.
                </p>
              </div>
              <div class="infobox-section">
                <p class="infobox-p">
                  <em>Relevance:</em>
                  A large glazing area is synonymous with large heating losses in a lot of cases, so targeting these buildings
                  for panelized retrofits makes sense. Windows are most often replaced in a panelized retrofit, where they can 
                  be ugraded to more energy efficient models.
                </p> 
              </div>
              <div class="infobox-section">
                <p class="infobox-p">
                  <em>Note:</em>
                  Please check all visible façades to answer this question. 
                </p> 
                <img class="infobox-img img-fluid" loading="lazy" src="/static/images/survey_info/q10_glazing/q10_glazing.jpg">  
              </div>
            </div>""",
            },
            "large_irregular_windows": {
                "title": "Large or Irregular Windows",
                "body": """<div>

              <div class="infobox-section">
                <em>Definition:</em>
                <p class="infobox-p">
                  A window is considered <strong>very large</strong> when it is larger than 2m (the usual height of a door) 
                  in any direction.
                </p>
                <p class="infobox-p">
                  A window is considered <strong>irregularly shaped</strong> if it is not a rectangle.
                </p>
              </div>
              <div class="infobox-section">
                <em>Relevance:</em>
                <p class="infobox-p">
                  Very large windows contribute significantly to heating and cooling loss, therefore buildings with 
                  large windows are likely to be energy inefficient, and therefore good candidates for retrofits.
                </p>
                <p class="infobox-p">
                  Irregularly shaped windows make a prefabricated panelized retrofit more difficult as panels need to 
                  be cut to shape. Additionally, they make the replication and scaling up of solutions infeasible since
                  panels must be addapted to the specific window. 
                </p>
              </div>
              <div class="infobox-section">
                <strong>Examples of very large windows:</strong>
                <img class="infobox-img img-fluid" loading="lazy" src="/static/images/survey_info/q11_largewindow/q11_examples.jpg">  
              </div>
              <div class="infobox-section">
                <strong>Example of large and irregular windows:</strong>
                <p class="infobox-p">The following building has both irregular (the small round ones and those with a rounded top) and large windows.</p>
                <img class="infobox-img img-fluid" loading="lazy" src="/static/images/survey_info/q11_largewindow/q11_irregular.jpg">  
              </div>
            </div>""",
            },
            "roof_geometry": {
                "title": "Roof Geometry",
                "body": """<div>
              <div class="infobox-section">
                <em>Definition:</em>
                <p class="infobox-p">
                  A pitched roof is a roof with a single slope (shed), or two slopes meeting (gable roof), 
                  or 4 slopes all meeting (pyramid). Whereas a complex roof may have multiple pitches and one 
                  or more other gables, or irregular shapes. 
                </p>
                <p class="infobox-p">
                  If a roof is pitched, it will have a pitch angle. A <strong>high pitch</strong> roof is anyone above a 6/12 in the roof pitch angle
                  diagram below, otherwise it is considered <strong>low pitch</strong>
                </p>
              </div>
              <div class="infobox-section">
                <em>Relevance:</em>
                <p class="infobox-p">
                  Complex and high pitch roofs increase the complexity of retrofit strategies in their analysis, design and 
                  installation processes, even making certain projects infeasible.
                </p>
              </div>
              <div class="infobox-section">
                <strong>Roof typologies:</strong>
                <img class="infobox-img img-fluid" loading="lazy" src="/static/images/survey_info/q12_rooftypes/q12_rooftypes.jpg">
              </div>
              <div class="infobox-section">
                <strong>Pitch angles:</strong>
                <img class="infobox-img img-fluid" loading="lazy" src="/static/images/survey_info/q12_rooftypes/q12_pitches.jpg">
              </div>
              <div class="infobox-section">
                <strong>Examples:</strong>
                <p class="infobox-p">
                  The following buildings both have a complex, high-pitched roof.
                </p>
                <img class="infobox-img img-fluid" loading="lazy" src="/static/images/survey_info/q12_rooftypes/high_pitched_complex.png">
                <img class="infobox-img img-fluid" loading="lazy" src="/static/images/survey_info/q12_rooftypes/high_pitched_complex_2.png">
              </div>
            </div>""",
            },
            "new_or_renovated": {
                "title": "New or Renovated Buildings",
                "body": """<div>
              <div class="infobox-section">
                <em>Definition:</em>
                <p>
                  If the building was built after the year 2000 or visually appears to be in exceptionally 
                  good condition with evidence of recent renovation, we can assume it has been recently renovated.   
                </p> 
              </div>
              <div class="infobox-section">
                <em>Relevance:</em>
                <p class="infobox-p">
                  New and renovated buildings are very poor candidates for retrofits since they are already in good 
                  condition and are likely to have decent energy performance. Retrofitting these buildings is most 
                  likely unjustifiable from a business/value case perspective, considering building investments are 
                  made with a 30-40y horizon.
                </p>
              </div>
            </div>""",
            },
        },
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
        schema={
            "appendages": {
                "pos": 7,
                "type": "text",
                "label": {"en": "Appendages"},
                "widget": "multi_checkbox_specify",
                "options": [
                    {"pos": 0, "val": "Balconies", "label": {"en": "Balconies"}},
                    {
                        "pos": 1,
                        "val": "Exterior Vestibules",
                        "label": {"en": "Exterior Vestibules"},
                    },
                    {
                        "pos": 2,
                        "val": "Roof overhangs/eaves",
                        "label": {"en": "Roof overhangs/eaves"},
                    },
                    {
                        "pos": 3,
                        "val": "Porches/stoops",
                        "label": {"en": "Porches/stoops"},
                    },
                    {
                        "pos": 4,
                        "val": "No obstructions",
                        "label": {"en": "No obstructions"},
                    },
                    {
                        "pos": 5,
                        "val": "Other (specify)",
                        "label": {"en": "Other (specify)"},
                    },
                ],
                "question_text": {
                    "en": "Select any and all significant appendages to the building faces."
                },
                "widget_config": {
                    "attrs": {"class": "survey-1col"},
                    "specify_input_type": "text",
                    "specify_option_value": "other",
                },
            },
            "num_storeys": {
                "pos": 4,
                "type": "integer",
                "label": {"en": "Number of Storeys"},
                "widget": "radio_w_specify",
                "options": [
                    {
                        "pos": 0,
                        "val": "Number of storeys",
                        "label": {"en": "Number of storeys"},
                    },
                    {"pos": 1, "val": None, "label": {"en": "Unsure"}},
                ],
                "question_text": {
                    "en": "How many storeys above-ground does the building have?"
                },
                "widget_config": {
                    "attrs": {"class": "survey-1col"},
                    "specify_input_type": "number",
                    "specify_option_value": "num_storeys",
                },
            },
            "has_basement": {
                "pos": 5,
                "type": "boolean_or_null",
                "label": {"en": "Has Basement"},
                "widget": "radio",
                "options": [
                    {"pos": 0, "val": True, "label": {"en": "Yes"}},
                    {"pos": 1, "val": False, "label": {"en": "No"}},
                    {"pos": 2, "val": None, "label": {"en": "Unsure"}},
                ],
                "question_text": {"en": "Does the building appear to have a basement?"},
                "widget_config": {"attrs": {"class": "survey-1col"}},
            },
            "roof_geometry": {
                "pos": 12,
                "type": "text",
                "label": {"en": "Roof Geometry"},
                "widget": "multi_checkbox",
                "options": [
                    {"pos": 0, "val": "Flat", "label": {"en": "Flat"}},
                    {"pos": 1, "val": "Curved", "label": {"en": "Curved"}},
                    {"pos": 2, "val": "Unsure", "label": {"en": "Unsure"}},
                    {"pos": 3, "val": "Complex", "label": {"en": "Complex"}},
                    {"pos": 4, "val": "Low Pitched", "label": {"en": "Low Pitched"}},
                    {"pos": 5, "val": "High Pitched", "label": {"en": "High Pitched"}},
                ],
                "question_text": {"en": "Select all that describes the roof geometry."},
                "widget_config": {
                    "is_required": True,
                    "attrs": {"class": "survey-3col"},
                },
            },
            "facade_condition": {
                "pos": 9,
                "type": "boolean_or_null",
                "label": {"en": "Facade Condition"},
                "widget": "radio",
                "options": [
                    {"pos": 0, "val": True, "label": {"en": "Yes"}},
                    {"pos": 1, "val": False, "label": {"en": "No"}},
                    {"pos": 2, "val": None, "label": {"en": "Unsure"}},
                ],
                "question_text": {
                    "en": "Are the façades in poor condition and in need of replacement?"
                },
                "widget_config": {"attrs": {"class": "survey-1col"}},
            },
            "new_or_renovated": {
                "pos": 13,
                "type": "text",
                "label": {"en": "New or Renovated"},
                "widget": "multi_checkbox",
                "options": [
                    {"pos": 0, "val": "Newly built", "label": {"en": "Newly built"}},
                    {
                        "pos": 1,
                        "val": "Recently renovated",
                        "label": {"en": "Recently renovated"},
                    },
                ],
                "question_text": {
                    "en": "Does the building look newly built or recently renovated?"
                },
            },
            "exterior_cladding": {
                "pos": 8,
                "type": "text",
                "label": {"en": "Exterior Cladding"},
                "widget": "multi_checkbox_specify",
                "options": [
                    {"pos": 0, "val": "Wood", "label": {"en": "Wood"}},
                    {"pos": 1, "val": "Metal", "label": {"en": "Metal"}},
                    {"pos": 2, "val": "Vinyl", "label": {"en": "Vinyl"}},
                    {"pos": 3, "val": "Plaster", "label": {"en": "Plaster"}},
                    {"pos": 4, "val": "Concrete", "label": {"en": "Concrete"}},
                    {"pos": 5, "val": "Curtain Wall", "label": {"en": "Curtain Wall"}},
                    {
                        "pos": 6,
                        "val": "Brick Masonry",
                        "label": {"en": "Brick Masonry"},
                    },
                    {
                        "pos": 7,
                        "val": "Stone Masonry",
                        "label": {"en": "Stone Masonry"},
                    },
                    {"pos": 8, "val": "Unsure", "label": {"en": "Unsure"}},
                    {"pos": 9, "val": "Other", "label": {"en": "Other (Specify)"}},
                ],
                "question_text": {
                    "en": "Select all types of exterior cladding does the building appear to have."
                },
                "widget_config": {
                    "attrs": {"class": "survey-3col"},
                    "is_required": True,
                    "specify_input_type": "text",
                    "specify_option_value": "Other",
                },
            },
            "has_simple_volume": {
                "pos": 3,
                "type": "boolean",
                "label": {"en": "Simple Volume"},
                "widget": "radio",
                "options": [
                    {"pos": 0, "val": True, "label": {"en": "Yes"}},
                    {"pos": 1, "val": False, "label": {"en": "No"}},
                ],
                "question_text": {
                    "en": "Does the building have a simple volumetric form?"
                },
            },
            "site_obstructions": {
                "pos": 6,
                "type": "text",
                "label": {"en": "Site Obstructions"},
                "widget": "multi_checkbox_specify",
                "options": [
                    {
                        "pos": 0,
                        "val": "Important trees or landscaping",
                        "label": {"en": "Important trees or landscaping"},
                    },
                    {"pos": 1, "val": "Buildings", "label": {"en": "Buildings"}},
                    {
                        "pos": 2,
                        "val": "Overhead wires",
                        "label": {"en": "Overhead wires"},
                    },
                    {
                        "pos": 3,
                        "val": "No obstructions",
                        "label": {"en": "No obstructions"},
                    },
                    {
                        "pos": 4,
                        "val": "Other (Specify)",
                        "label": {"en": "Other (Specify)"},
                    },
                ],
                "question_text": {
                    "en": "Select any and all obstructions to machine access around the building."
                },
            },
            "window_wall_ratio": {
                "pos": 10,
                "type": "boolean_or_null",
                "label": {"en": "Window-to-Wall Ratio"},
                "widget": "radio",
                "options": [
                    {"pos": 0, "val": True, "label": {"en": "Yes"}},
                    {"pos": 1, "val": False, "label": {"en": "No"}},
                    {"pos": 2, "val": None, "label": {"en": "Unsure"}},
                ],
                "question_text": {
                    "en": "Does glazing make up more than 40% of the total visible façade area?"
                },
                "widget_config": {"attrs": {"class": "survey-1col"}},
            },
            "has_simple_footprint": {
                "pos": 2,
                "type": "boolean",
                "label": {"en": "Simple Footprint"},
                "widget": "radio",
                "options": [
                    {"pos": 0, "val": True, "label": {"en": "Yes"}},
                    {"pos": 1, "val": False, "label": {"en": "No"}},
                ],
                "question_text": {"en": "Does the building have a simple footprint?"},
            },
            "self_similar_cluster": {
                "pos": 1,
                "type": "integer",
                "label": {"en": "Self Similar Cluster"},
                "widget": "radio_w_specify",
                "options": [
                    {
                        "pos": 0,
                        "val": "Buildings in cluster",
                        "label": {"en": "Buildings in cluster"},
                    },
                    {"pos": 1, "val": None, "label": {"en": "No"}},
                ],
                "question_text": {
                    "en": "Is the building part of a self-similar cluster? If so, how many buildings are in the cluster?"
                },
                "widget_config": {
                    "specify_input_type": "number",
                    "specify_option_value": "Buildings in cluster",
                },
            },
            "large_irregular_windows": {
                "pos": 11,
                "type": "text",
                "label": {"en": "Large/Irregular Windows"},
                "widget": "multi_checkbox",
                "options": [
                    {
                        "pos": 1,
                        "val": "Irregularly shaped",
                        "label": {"en": "Irregularly shaped"},
                    },
                    {
                        "pos": 0,
                        "val": "Very large",
                        "label": {"en": "Very large"},
                    },
                ],
                "question_text": {
                    "en": "Are there very large and/or irregularly shaped windows?"
                },
                "widget_config": {"attrs": {"class": "survey-1col"}},
            },
        },
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
