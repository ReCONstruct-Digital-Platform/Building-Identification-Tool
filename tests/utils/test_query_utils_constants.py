dataset_query_1 = {
    "query": {
        "condition": "AND",
        "rules": [
            {
                "id": "const_year",
                "field": "const_year",
                "type": "date",
                "input": "text",
                "operator": "between",
                "value": [1950, 2000],
            },
            {
                "condition": "OR",
                "rules": [
                    {
                        "id": "num_floors",
                        "field": "num_floors",
                        "type": "integer",
                        "input": "number",
                        "operator": "greater",
                        "value": 1,
                    },
                    {
                        "id": "attrs__phys_link",
                        "field": "attrs__phys_link",
                        "type": "string",
                        "input": "checkbox",
                        "operator": "in",
                        "value": ["semi-detached", "row house"],
                    },
                ],
            },
        ],
        "valid": True,
    }
}


dataset_schema = [
    {
        "id": "ext_id",
        "type": "string",
        "field": "ext_id",
        "input": "text",
        "label": {"en": "External ID"},
        "optgroup": "core",
    },
    {
        "id": "address",
        "type": "string",
        "field": "address",
        "input": "text",
        "label": {"en": "Address"},
        "optgroup": "core",
    },
    {
        "id": "street_name",
        "type": "string",
        "field": "street_name",
        "input": "text",
        "label": {"en": "Street Name"},
        "optgroup": "core",
    },
    {
        "id": "street_num",
        "type": "string",
        "field": "street_num",
        "input": "text",
        "label": {"en": "Street Number"},
        "optgroup": "core",
    },
    {
        "id": "muni",
        "type": "string",
        "field": "muni",
        "input": "text",
        "label": {"en": "Municipality"},
        "optgroup": "core",
    },
    {
        "id": "submuni",
        "type": "string",
        "field": "submuni",
        "input": "text",
        "label": {"en": "Submunicipality"},
        "optgroup": "core",
    },
    {
        "id": "postal_code",
        "type": "string",
        "field": "postal_code",
        "input": "text",
        "label": {"en": "Postal Code"},
        "optgroup": "core",
    },
    {
        "id": "const_year",
        "type": "date",
        "field": "const_year",
        "label": {"en": "Construction Year"},
        "plugin": "datepicker",
        "optgroup": "core",
        "plugin_config": {
            "format": "yyyy",
            "todayBtn": "linked",
            "autoclose": True,
            "minViewMode": "years",
            "todayHighlight": True,
        },
    },
    {
        "id": "num_floors",
        "type": "integer",
        "field": "num_floors",
        "input": "number",
        "label": {"en": "Num. Floors"},
        "optgroup": "core",
    },
    {
        "id": "floor_area",
        "type": "double",
        "field": "floor_area",
        "input": "number",
        "label": {"en": "Floor area"},
        "optgroup": "core",
        "validation": {"min": 0, "step": 0.01},
    },
    {
        "id": "attrs__organism",
        "type": "string",
        "field": "attrs__organism",
        "input": "text",
        "label": {"en": "Organism"},
        "optgroup": "attributes",
    },
    {
        "id": "attrs__service_center",
        "type": "string",
        "field": "attrs__service_center",
        "input": "text",
        "label": {"en": "Service Center"},
        "optgroup": "attributes",
    },
    {
        "id": "attrs__area_footprint",
        "type": "double",
        "field": "attrs__area_footprint",
        "input": "number",
        "label": {"en": "Footprint Area"},
        "optgroup": "attributes",
        "validation": {"min": 0, "step": 0.01},
    },
    {
        "id": "attrs__area_total",
        "type": "double",
        "field": "attrs__area_total",
        "input": "number",
        "label": {"en": "Total Area"},
        "optgroup": "attributes",
        "validation": {"min": 0, "step": 0.01},
    },
    {
        "id": "attrs__ivp",
        "type": "double",
        "field": "attrs__ivp",
        "input": "number",
        "label": {"en": "IVP"},
        "optgroup": "attributes",
        "validation": {"min": 0, "step": 0.01},
    },
    {
        "id": "attrs__disrepair_state",
        "type": "string",
        "field": "attrs__disrepair_state",
        "input": "checkbox",
        "label": {"en": "Disrepair State"},
        "values": ["A", "B", "C", "D", "E"],
        "optgroup": "attributes",
    },
    {
        "id": "attrs__interest_adjust_date",
        "type": "date",
        "field": "attrs__interest_adjust_date",
        "label": {"en": "Interest Adjustment Date"},
        "plugin": "datepicker",
        "optgroup": "attributes",
        "plugin_config": {
            "format": "yyyy-mm-dd",
            "todayBtn": "linked",
            "autoclose": True,
            "todayHighlight": True,
        },
    },
    {
        "id": "attrs__contract_end_date",
        "type": "date",
        "field": "attrs__contract_end_date",
        "label": {"en": "Contract End Date"},
        "plugin": "datepicker",
        "optgroup": "attributes",
        "plugin_config": {
            "format": "yyyy-mm-dd",
            "todayBtn": "linked",
            "autoclose": True,
            "todayHighlight": True,
        },
    },
    {
        "id": "attrs__category",
        "type": "string",
        "field": "attrs__category",
        "input": "text",
        "label": {"en": "Category"},
        "optgroup": "attributes",
    },
    {
        "id": "attrs__building_id",
        "type": "string",
        "field": "attrs__building_id",
        "input": "text",
        "label": {"en": "Building ID"},
        "optgroup": "attributes",
    },
    {
        "id": "attrs__phys_link",
        "type": "string",
        "field": "attrs__phys_link",
        "input": "checkbox",
        "label": {"en": "Physical Link"},
        "values": [
            "row house (one side)",
            "semi-detached",
            "single-detached",
            "integrated",
            "row house",
        ],
        "optgroup": "attributes",
        "operators": ["in", "not_in", "is_null", "is_not_null"],
    },
    {
        "id": "attrs__const_type",
        "type": "string",
        "field": "attrs__const_type",
        "input": "checkbox",
        "label": {"en": "Construction Type"},
        "values": [
            "attic",
            "single-storey",
            "staggered-level",
            "modular prefab",
            "full-storey",
        ],
        "optgroup": "attributes",
         "operators": ["in", "not_in", "is_null", "is_not_null"],
    },
    {
        "id": "attrs__owner_date",
        "type": "date",
        "field": "attrs__owner_date",
        "label": {"en": "Owner Date"},
        "plugin": "datepicker",
        "optgroup": "attributes",
        "plugin_config": {
            "format": "yyyy-mm-dd",
            "todayBtn": "linked",
            "autoclose": True,
            "todayHighlight": True,
        },
    },
    {
        "id": "attrs__owner_type",
        "type": "string",
        "field": "attrs__owner_type",
        "input": "checkbox",
        "label": {"en": "Owner Type"},
        "values": ["moral", "physical"],
        "optgroup": "attributes",
        "operators": ["in", "not_in", "is_null", "is_not_null"],
    },
    {
        "id": "attrs__owner_status",
        "type": "string",
        "field": "attrs__owner_status",
        "input": "checkbox",
        "label": {"en": "Owner Status"},
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
        "optgroup": "attributes",
        "operators": ["in", "not_in", "is_null", "is_not_null"],
    },
    {
        "id": "attrs__lot_lin_dim",
        "type": "double",
        "field": "attrs__lot_lin_dim",
        "input": "number",
        "label": {"en": "Lot Linear Dimension"},
        "optgroup": "attributes",
        "validation": {"min": 0, "step": 0.01},
    },
    {
        "id": "attrs__lot_area",
        "type": "double",
        "field": "attrs__lot_area",
        "input": "number",
        "label": {"en": "Lot Area"},
        "optgroup": "attributes",
        "validation": {"min": 0, "step": 0.01},
    },
    {
        "id": "attrs__apprais_date",
        "type": "date",
        "field": "attrs__apprais_date",
        "label": {"en": "Appraisal Date"},
        "plugin": "datepicker",
        "optgroup": "attributes",
        "plugin_config": {
            "format": "yyyy-mm-dd",
            "todayBtn": "linked",
            "autoclose": True,
            "todayHighlight": True,
        },
    },
    {
        "id": "attrs__lot_value",
        "type": "double",
        "field": "attrs__lot_value",
        "input": "number",
        "label": {"en": "Lot Value"},
        "optgroup": "attributes",
        "validation": {"min": 0, "step": 0.01},
    },
    {
        "id": "attrs__building_value",
        "type": "double",
        "field": "attrs__building_value",
        "input": "number",
        "label": {"en": "Building Value"},
        "optgroup": "attributes",
        "validation": {"min": 0, "step": 0.01},
    },
    {
        "id": "attrs__value",
        "type": "double",
        "field": "attrs__value",
        "input": "number",
        "label": {"en": "Value"},
        "optgroup": "attributes",
        "validation": {"min": 0, "step": 0.01},
    },
    {
        "id": "attrs__prev_value",
        "type": "double",
        "field": "attrs__prev_value",
        "input": "number",
        "label": {"en": "Previous Value"},
        "optgroup": "attributes",
        "validation": {"min": 0, "step": 0.01},
    },
]


survey_schema = {
    "appendages": {
        "label": "Appendages",
        "values": {
            "balconies": {"question_text": {"en": "Balconies"}},
            "vestibules": {"question_text": {"en": "Exterior Vestibules"}},
            "canopies_eaves": {"question_text": {"en": "Roof overhangs/eaves"}},
            "porches_stoops": {"question_text": {"en": "Porches/stoops"}},
        },
        "widget": "multi_checkbox_specify",
        "question_text": {
            "en": "Select any and all significant appendages to the building faces."
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
    "roof_geometry": {
        "label": "Roof Geometry",
        "values": {
            "flat": {"question_text": {"en": "Flat"}},
            "curved": {"question_text": {"en": "Curved"}},
            "unsure": {"question_text": {"en": "Unsure"}},
            "complex": {"question_text": {"en": "Complex"}},
            "pitch_low": {"question_text": {"en": "Low Pitched"}},
            "pitch_high": {"question_text": {"en": "High Pitched"}},
        },
        "widget": "multi_checkbox_specify_required",
        "question_text": {"en": "Select all that describes the roof geometry?"},
    },
    "facade_condition": {
        "label": "Facade Condition",
        "widget": "boolean",
        "question_text": {
            "en": "Are the façades in poor condition and in need of replacement?"
        },
    },
    "new_or_renovated": {
        "label": "New or Renovated",
        "values": {
            "newly_built": {"question_text": {"en": "Newly built"}},
            "recently_renovated": {"question_text": {"en": "Recently renovated"}},
        },
        "widget": "multi_checkbox_specify",
        "question_text": {
            "en": "Does the building look newly built or recently renovated?"
        },
    },
    "exterior_cladding": {
        "label": "Exterior Cladding",
        "values": {
            "wood": {"question_text": {"en": "Wood"}},
            "metal": {"question_text": {"en": "Metal"}},
            "vinyl": {"question_text": {"en": "Vinyl"}},
            "unsure": {"question_text": {"en": "Unsure"}},
            "plaster": {"question_text": {"en": "Plaster"}},
            "concrete": {"question_text": {"en": "Concrete"}},
            "curtain_wall": {"question_text": {"en": "Curtain Wall"}},
            "brick_masonry": {"question_text": {"en": "Brick Masonry"}},
            "stone_masonry": {"question_text": {"en": "Stone Masonry"}},
        },
        "widget": "multi_checkbox_specify_required",
        "question_text": {
            "en": "Select all widgets of exterior cladding does the building appear to have."
        },
    },
    "has_simple_volume": {
        "label": "Simple Volume",
        "widget": "boolean",
        "question_text": {"en": "Does the building have a simple volumetric form?"},
    },
    "site_obstructions": {
        "label": "Site Obstructions",
        "values": {
            "buildings": {"question_text": {"en": "Buildings"}},
            "overhead_wires": {
                "question_text": {
                    "en": "Overhead wires, incl. those blocking general access to site"
                }
            },
            "trees_or_landscaping": {
                "question_text": {"en": "Important trees or landscaping"}
            },
        },
        "widget": "multi_checkbox_specify",
        "question_text": {
            "en": "Select any and all obstructions to machine access around the building."
        },
    },
    "window_wall_ratio": {
        "label": "Window-to-Wall Ratio",
        "widget": "boolean",
        "question_text": {
            "en": "Does glazing make up more than 40% of the total visible façade area?"
        },
    },
    "has_simple_footprint": {
        "label": "Simple Footprint",
        "widget": "boolean",
        "question_text": {"en": "Does the building have a simple footprint?"},
    },
    "self_similar_cluster": {
        "label": "Self Similar Cluster",
        "widget": "radio_specify_integer",
        "question_text": {
            "en": "Is the building part of a self-similar cluster? If so, how many buildings are in the cluster?"
        },
    },
    "large_irregular_windows": {
        "label": "Large/Irregular Windows",
        "widget": "boolean",
        "question_text": {
            "en": "Are there very large and/or irregularly shaped windows?"
        },
    },
}
