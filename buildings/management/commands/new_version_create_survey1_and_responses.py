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
        schema={
            "appendages": {
                "type": "text",
                "label": {"en": "Appendages"},
                "widget": "multi_checkbox_specify",
                "options": [
                    {"val": "balconies", "label": {"en": "Balconies"}, "pos": 0},
                    {
                        "val": "vestibules",
                        "label": {"en": "Exterior Vestibules"},
                        "pos": 1,
                    },
                    {
                        "val": "canopies_eaves",
                        "label": {"en": "Roof overhangs/eaves"},
                        "pos": 2,
                    },
                    {
                        "val": "porches_stoops",
                        "label": {"en": "Porches/stoops"},
                        "pos": 3,
                    },
                    {"val": "other", "label": {"en": "Other (specify)"}, "pos": 4},
                ],
                "question_text": {
                    "en": "Select any and all significant appendages to the building faces."
                },
                "widget_config": {
                    "attrs": {"class": "survey-1col"},
                    "specify_input_type": "text",
                    "specify_option_value": "other",
                },
                "pos": 7,
            },
            "num_storeys": {
                "type": "integer",
                "label": {"en": "Number of Storeys"},
                "widget": "radio_w_specify",
                "options": [
                    {
                        "val": "num_storeys",
                        "label": {"en": "Number of storeys"},
                        "pos": 0,
                    },
                    {"val": None, "label": {"en": "Unsure"}, "pos": 1},
                ],
                "question_text": {
                    "en": "How many storeys above-ground does the building have?"
                },
                "widget_config": {
                    "attrs": {"class": "survey-1col"},
                    "specify_input_type": "number",
                    "specify_option_value": "num_storeys",
                },
                "pos": 4,
            },
            "has_basement": {
                "type": "boolean",
                "label": {"en": "Has Basement"},
                "widget": "radio",
                "options": [
                    {"val": True, "label": {"en": "Yes"}, "pos": 0},
                    {"val": False, "label": {"en": "No"}, "pos": 1},
                    {"val": None, "label": {"en": "Unsure"}, "pos": 2},
                ],
                "question_text": {"en": "Does the building appear to have a basement?"},
                "widget_config": {"attrs": {"class": "survey-1col"}},
                "pos": 5,
            },
            "roof_geometry": {
                "type": "text",
                "label": {"en": "Roof Geometry"},
                "widget": "multi_checkbox_required",
                "options": [
                    {"val": "flat", "label": {"en": "Flat"}, "pos": 0},
                    {"val": "curved", "label": {"en": "Curved"}, "pos": 1},
                    {"val": "unsure", "label": {"en": "Unsure"}, "pos": 2},
                    {"val": "complex", "label": {"en": "Complex"}, "pos": 3},
                    {"val": "pitch_low", "label": {"en": "Low Pitched"}, "pos": 4},
                    {"val": "pitch_high", "label": {"en": "High Pitched"}, "pos": 5},
                ],
                "question_text": {"en": "Select all that describes the roof geometry."},
                "widget_config": {"attrs": {"class": "survey-3col"}},
                "pos": 12,
            },
            "facade_condition": {
                "type": "boolean",
                "label": {"en": "Facade Condition"},
                "widget": "radio",
                "options": [
                    {"val": True, "label": {"en": "Yes"}, "pos": 0},
                    {"val": False, "label": {"en": "No"}, "pos": 1},
                    {"val": None, "label": {"en": "Unsure"}, "pos": 2},
                ],
                "question_text": {
                    "en": "Are the façades in poor condition and in need of replacement?"
                },
                "widget_config": {"attrs": {"class": "survey-1col"}},
                "pos": 9,
            },
            "new_or_renovated": {
                "type": "text",
                "label": {"en": "New or Renovated"},
                "widget": "multi_checkbox",
                "options": [
                    {"val": "newly_built", "label": {"en": "Newly built"}, "pos": 0},
                    {
                        "val": "recently_renovated",
                        "label": {"en": "Recently renovated"},
                        "pos": 1,
                    },
                ],
                "question_text": {
                    "en": "Does the building look newly built or recently renovated?"
                },
                "pos": 13,
            },
            "exterior_cladding": {
                "type": "text",
                "label": {"en": "Exterior Cladding"},
                "widget": "multi_checkbox_required_specify",
                "options": [
                    {"val": "wood", "label": {"en": "Wood"}, "pos": 0},
                    {"val": "metal", "label": {"en": "Metal"}, "pos": 1},
                    {"val": "vinyl", "label": {"en": "Vinyl"}, "pos": 2},
                    {"val": "plaster", "label": {"en": "Plaster"}, "pos": 3},
                    {"val": "concrete", "label": {"en": "Concrete"}, "pos": 4},
                    {"val": "curtain_wall", "label": {"en": "Curtain Wall"}, "pos": 5},
                    {
                        "val": "brick_masonry",
                        "label": {"en": "Brick Masonry"},
                        "pos": 6,
                    },
                    {
                        "val": "stone_masonry",
                        "label": {"en": "Stone Masonry"},
                        "pos": 7,
                    },
                    {"val": "unsure", "label": {"en": "Unsure"}, "pos": 8},
                    {"val": "other", "label": {"en": "Other (Specify)"}, "pos": 9},
                ],
                "question_text": {
                    "en": "Select all types of exterior cladding does the building appear to have."
                },
                "widget_config": {
                    "attrs": {"class": "survey-3col"},
                    "specify_input_type": "text",
                    "specify_option_value": "other",
                },
                "pos": 8,
            },
            "has_simple_volume": {
                "type": "boolean",
                "label": {"en": "Simple Volume"},
                "widget": "radio",
                "options": [
                    {"val": True, "label": {"en": "Yes"}, "pos": 0},
                    {"val": False, "label": {"en": "No"}, "pos": 1},
                ],
                "question_text": {
                    "en": "Does the building have a simple volumetric form?"
                },
                "pos": 3,
            },
            "site_obstructions": {
                "type": "text",
                "label": {"en": "Site Obstructions"},
                "widget": "multi_checkbox_specify",
                "options": [
                    {
                        "val": "trees_or_landscaping",
                        "label": {"en": "Important trees or landscaping"},
                        "pos": 0,
                    },
                    {"val": "buildings", "label": {"en": "Buildings"}, "pos": 1},
                    {
                        "val": "overhead_wires",
                        "label": {
                            "en": "Overhead wires, incl. those blocking general access to site"
                        },
                        "pos": 2,
                    },
                    {"val": "other", "label": {"en": "Other (Specify)"}, "pos": 3},
                ],
                "question_text": {
                    "en": "Select any and all obstructions to machine access around the building."
                },
                "pos": 6,
            },
            "window_wall_ratio": {
                "type": "boolean",
                "label": {"en": "Window-to-Wall Ratio"},
                "widget": "radio",
                "options": [
                    {"val": True, "label": {"en": "Yes"}, "pos": 0},
                    {"val": False, "label": {"en": "No"}, "pos": 1},
                    {"val": None, "label": {"en": "Unsure"}, "pos": 2},
                ],
                "question_text": {
                    "en": "Does glazing make up more than 40% of the total visible façade area?"
                },
                "widget_config": {"attrs": {"class": "survey-1col"}},
                "pos": 10,
            },
            "has_simple_footprint": {
                "type": "boolean",
                "label": {"en": "Simple Footprint"},
                "widget": "radio",
                "options": [
                    {"val": True, "label": {"en": "Yes"}, "pos": 0},
                    {"val": False, "label": {"en": "No"}, "pos": 1},
                ],
                "question_text": {"en": "Does the building have a simple footprint?"},
                "pos": 2,
            },
            "self_similar_cluster": {
                "type": "integer",
                "label": {"en": "Self Similar Cluster"},
                "widget": "radio_w_specify",
                "options": [
                    {
                        "val": "num_buildings_in_cluster",
                        "label": {"en": "Buildings in cluster"},
                        "pos": 0,
                    },
                    {"val": None, "label": {"en": "No"}, "pos": 1},
                ],
                "question_text": {
                    "en": "Is the building part of a self-similar cluster? If so, how many buildings are in the cluster?"
                },
                "widget_config": {
                    "specify_input_type": "number",
                    "specify_option_value": "num_buildings_in_cluster",
                },
                "pos": 1,
            },
            "large_irregular_windows": {
                "type": "text",
                "label": {"en": "Large/Irregular Windows"},
                "widget": "multi_checkbox",
                "options": [
                    {
                        "val": "irregular_windows",
                        "label": {"en": "Irregularly shaped"},
                        "pos": 1,
                    },
                    {
                        "val": "very_large_windows",
                        "label": {"en": "Very large"},
                        "pos": 0,
                    },
                ],
                "question_text": {
                    "en": "Are there very large and/or irregularly shaped windows?"
                },
                "widget_config": {"attrs": {"class": "survey-1col"}},
                "pos": 11,
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
