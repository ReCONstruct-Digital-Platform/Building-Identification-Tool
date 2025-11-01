from django.conf import settings
from django.contrib.gis.db import models
from django.db.models import JSONField, Count
from django.utils import timezone
from autoslug import AutoSlugField

from django.db.models.expressions import RawSQL
from django.utils.translation import gettext_lazy as _

from buildings.models.constants import DATASET_BASE_SCHEMA
from buildings.utils.b2 import (
    create_presigned_url,
)
from buildings.utils.query_utils import DatasetQParser, SurveyQParser


class Dataset(models.Model):
    class Meta:
        db_table = "datasets"

    name = models.TextField()
    description = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    slug = AutoSlugField(populate_from="name")
    # Contains the schema of both the static and dynamic fields of
    # the associated models. Static fields that are not present are null.
    schema = JSONField()

    BASE_SCHEMA = DATASET_BASE_SCHEMA

    def get_schema(self, prefix=None):
        if prefix:
            # Prepend prefix to the id of each field
            # This overwrites id and field from the schema
            return list(
                map(
                    lambda f: {
                        **f,
                        "id": f"{prefix}{f['id']}",
                        "field": f"{prefix}{f['field']}",
                    },
                    self.schema,
                )
            )
        return self.schema

    date_added = models.DateTimeField("date added", default=timezone.now)
    date_modified = models.DateTimeField("date modified", default=timezone.now)

    def get_fields_to_display(self):
        """
        Returns a few select fields from the shared fields, and all the dynamic attributes
        """
        return [
            {"id": a["id"], "label": a["label"]["en"]}
            for a in self.schema
            if a["id"]
            in [
                "ext_id",
                "submuni",
                "const_year",
                "num_floors",
                "floor_area",
                "postal_code",
                "geocoding_error",
            ]
            or "attrs" in a["id"]
        ]

    def get_orderby_fields(self):
        """
        Returns all fields from the schema for ordering
        """
        return [{"id": a["id"], "label": a["label"]["en"]} for a in self.schema]


class UserConfigs(models.Model):
    """
    Hold various user display configs
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    # JSON converts the keys from int to string
    res_page_bldg_cols = models.JSONField(null=True, blank=True, default=dict)
    res_page_survey_cols = models.JSONField(null=True, blank=True, default=dict)
    sur_page_bldg_cols = models.JSONField(null=True, blank=True, default=dict)

    def get_survey_page_building_columns(self, survey):
        """
        Returns the survey page columns to display config or None
        """
        if self.sur_page_bldg_cols:
            return self.sur_page_bldg_cols.get(str(survey.id), None)
        return None

    def get_results_page_survey_column_config(self, survey):
        """
        Returns the survey page columns to display config or None
        """
        if self.res_page_survey_cols:
            return self.res_page_survey_cols.get(str(survey.id), None)
        return None

    def get_results_page_dataset_column_config(self, dataset):
        """
        Returns the survey page columns to display config or None
        """
        if self.res_page_bldg_cols:
            return self.res_page_bldg_cols.get(str(dataset.id), None)
        return None


class Building(models.Model):
    """
    Base building class.
    The objects of Surveys.
    """

    # Can be changed without creating a new migration
    # TODO: Adding the dataset name guarantees no conflicts for two datasets with same building
    # which could become interesting with multiple users but leads to potential long names
    def slugify(instance):
        fields = [
            instance.dataset.name,
            instance.address,
            instance.submuni,
            instance.muni,
        ]
        fields = [f for f in fields if f is not None]
        return " ".join(fields)

    class Meta:
        db_table = "buildings"
        unique_together = ("ext_id", "lat", "lng", "address", "muni")

    # optional external ID field
    ext_id = models.TextField(null=True, blank=True)

    lat = models.FloatField(null=True)
    lng = models.FloatField(null=True)
    point = models.PointField(null=True, spatial_index=True)

    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)

    # Have a full text search index on this
    address = models.TextField()

    # See https://developers.google.com/maps/documentation/geocoding/requests-geocoding#results
    # and https://docs.mapbox.com/api/search/geocoding/#response-forward-geocoding-with-search-text-input
    # for possible fields to be filled in
    street_name = models.TextField(null=True)
    street_num = models.TextField(null=True)
    street_num_2 = models.TextField(null=True, blank=True)

    muni = models.TextField(null=True, blank=True)
    submuni = models.TextField(null=True, blank=True)
    # Provinces / States
    # See https://developers.google.com/maps/documentation/geocoding/requests-geocoding#Types
    admin_area_level_1 = models.TextField(null=True, blank=True)
    postal_code = models.TextField(null=True, blank=True)

    # TODO: maybe these should be attributes
    const_year = models.SmallIntegerField(null=True, blank=True)
    num_floors = models.IntegerField(null=True, blank=True)
    floor_area = models.FloatField(null=True, blank=True)

    # Field to store geocoding errors
    geocoding_error = models.TextField(null=True, blank=True)
    has_streetview = models.BooleanField(null=True)

    # JSONB field to hold an object of dynamic attributes
    attrs = models.JSONField(null=True, blank=True)

    # User-friendly URL slug
    slug = AutoSlugField(populate_from=slugify, max_length=200)

    has_thumbnail = models.BooleanField(default=False)

    date_added = models.DateTimeField("date added", default=timezone.now)
    date_modified = models.DateTimeField("date modified", default=timezone.now)

    def get_field(self, key):
        if "attrs__" in key:
            return self.attrs[key.replace("attrs__", "")]
        return getattr(self, key)

    def get_attrs(self):
        attrs_fields = [
            {"id": a["id"].replace("attrs__", ""), "label": a["label"]["en"]}
            for a in self.dataset.schema
            if ("attrs__" in a["id"])
        ]
        return attrs_fields

    def get_responses_for_survey(self, survey):
        return self.response_set.filter(survey=survey)

    def get_thumbnail_url(self):
        # Constant thumbnail key for all buildings
        thumbnail_key = f"reconstruct/{self.dataset.slug}/{self.slug}/thumbnail.jpg"
        return create_presigned_url(thumbnail_key)

    def get_all_small_image_urls(self):
        return self.get_images_presigned_urls("s")

    def get_all_medium_image_urls(self):
        return self.get_images_presigned_urls("m")

    def get_all_large_image_urls(self):
        return self.get_images_presigned_urls("l")

    def get_images_presigned_urls(self, size="s"):
        # TODO add tenant
        prefix = f"reconstruct/{self.dataset.slug}/{self.slug}/{size}"

        all_images = BuildingImage.objects.filter(building=self)

        return [create_presigned_url(f"{prefix}/{img.filename}") for img in all_images]

    def __str__(self):
        base_str = (
            f"Building {self.id}: {self.address}, {self.muni}, {self.postal_code}"
        )
        if self.geocoding_error:
            return f"{base_str} [Error: {self.geocoding_error}]"
        return base_str


class Survey(models.Model):
    """
    Surveys are linked to a source dataset and target a subset of buildings.
    The subset of buildings is defined through a filter on the source dataset.

    Sub-surveys are defined by an additional filter on other surveys' responses on
    the source dataset's buildings.
    """

    class Meta:
        db_table = "surveys"
        unique_together = (
            "name",
            "dataset",
            "dataset_filter",
            "surveys_filter",
        )

    class Status(models.TextChoices):
        DRAFT = "DRAFT", _("Draft")
        ACTIVE = "ACTIVE", _("Active")
        COMPLETED = "COMPLETED", _("Completed")
        ARCHIVED = "ARCHIVED", _("Archived")

    status = models.TextField(choices=Status.choices, default=Status.DRAFT)

    name = models.TextField()
    description = models.TextField(null=True, blank=True)
    slug = AutoSlugField(populate_from="name", unique=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    # Source dataset
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)

    # Filter on the upstream dataset's columns and json attributes
    # JSON necessary to construct a Q object on the source dataset
    # Can be fed to Q to create an ORM filter
    dataset_filter = models.JSONField(null=True, blank=True)

    # Survey schema is a mapping of field_id -> (field_label, type, question_text, widget)
    schema = JSONField(default=dict)

    # Holds modal HTML
    modals = JSONField(null=True, blank=True)

    # Filter on any existing survey results for the dataset
    # a mapping of survey_id -> {[survey_field]: [conditions]}
    # Can be fed to Q to create an ORM filter
    surveys_filter = models.JSONField(null=True, blank=True)

    date_added = models.DateTimeField("date added", default=timezone.now)
    date_modified = models.DateTimeField("date modified", default=timezone.now)

    def get_readonly_rules(self, type: str):
        if type not in ["dataset", "surveys"]:
            raise Exception(f"Unknown readonly type: {type}")
        filter = getattr(self, f"{type}_filter")
        if filter is None:
            return None
        readonly_rules = []
        for rule in filter["rules"]:
            rule["readonly"] = True
            readonly_rules.append(rule)
        filter["rules"] = readonly_rules
        filter["readonly"] = True
        return filter

    def get_filters_from_rules(self, rules):
        filters = []
        for rule in rules["rules"]:
            if "rules" in rule:
                filters.append(self.get_filters_from_rules(rule))
            else:
                filters.append(
                    {
                        "id": rule["id"],
                        "field": rule["field"],
                        "type": rule["type"],
                        "input": rule["input"],
                    }
                )
        return filters

    def get_columns_to_display(self):
        """
        Returns the schema columns in a nice format to be displayed
        """
        return [{"id": f, "label": v["label"]["en"]} for f, v in self.schema.items()]

    def get_results(self, add_num_responses=True):
        # Ensure the dataset and the linked responses survey matches
        qs = Building.objects.filter(dataset=self.dataset, response__survey=self)

        if add_num_responses:
            qs = qs.annotate(num_responses=Count("response"))

        return qs.annotate(
            response_data=RawSQL(
                """
                    --- Create JSON objects for each building containing all the response data for each survey
                    select jsonb_object_agg(key, value)
                    from (
                        --- Merge response data by building id and by key. 
                        --- For each Building, there is a line for each key containing an array 
                        --- of all values that were present in the response data. 
                        select 
                            id, key, jsonb_agg(distinct value) as value
                        from (
                            --- Explode the data again. Now for each response data key, there is a line 
                            --- for each value present originally, either in an array or as a scalar. 
                            select 
                                id, key, jsonb_array_elements(value) as value
                            from (
                                --- Convert all values to arrays. 
                                select 
                                    id, key,
                                    case jsonb_typeof(value)
                                        when 'array' then value
                                        else jsonb_build_array(value)
                                    end as value
                                from (
                                    --- For each Response, return one line per key in the response data JSON
                                    --- prepend the survey id to each response data key. 
                                    --- Some values are arrays, some are scalars.
                                    select 
                                        r.building_id as id,
                                        (jsonb_each(r.data)).key as key, 
                                        (jsonb_each(r.data)).value 
                                    from responses r
                                    where r.building_id = buildings.id
                                    --- THIS IS DIFFERENT FROM THE TARGET POPULATION QUERY
                                    and r.survey_id = %s
                                ) as sub
                            ) as sub2
                        ) as sub3    
                        group by id, key
                    ) as sub4
                    group by id""",
                (self.id,),
                output_field=models.JSONField(),
            )
        )

    # If this gets slow, implement a view for the target population
    # mapping building_id -> aggregated response data
    # IT will have to refresh everytime a new response is added
    # https://www.fusionbox.com/blog/detail/using-materialized-views-to-implement-efficient-reports-in-django/643/
    # https://pypi.org/project/django-db-views/
    #
    # Other option to optimize: having a separate table with the target population
    # means we don't need to fun this query to get target pop, it would just be saved in the DB
    #
    def get_target_population(
        self, dataset_schema=None, dataset_filter=None, surveys_filter=None
    ):
        # Support calling this method with different filters
        # or the Survey instance's filters if not provided
        if dataset_schema is None:
            dataset_schema = self.dataset.schema
        if dataset_filter is None:
            dataset_filter = self.dataset_filter
        if surveys_filter is None:
            surveys_filter = self.surveys_filter

        # Start with all buildings in the source dataset
        candidates = Building.objects.filter(dataset=self.dataset)

        # Filter on building attributes if applicable
        if dataset_filter is not None:
            dataset_q_parser = DatasetQParser(schema=dataset_schema)
            dataset_q = dataset_q_parser.parse_query(dataset_filter)
            candidates = candidates.filter(dataset_q)

        # Filter on past surveys results if applicable.
        # Annotate Buildings of the source dataset with all the response
        # data for any survey. Then filter using our surveys_filter.
        # An optimized version of this would check which surveys are being filtered
        # and only join the responses for these ones.
        if surveys_filter is not None:
            survey_q_parser = SurveyQParser()
            surveys_q = survey_q_parser.parse_query(surveys_filter)

            candidates = candidates.annotate(
                response_data=RawSQL(
                    """
                    --- Create JSON objects for each building containing all the response data for each survey
                    select jsonb_object_agg(key, value)
                    from (
                        --- Merge response data by building id and by key. 
                        --- For each Building, there is a line for each key containing an array 
                        --- of all values that were present in the response data. 
                        select 
                            id, key, jsonb_agg(distinct value) as value
                        from (
                            --- Explode the data again. Now for each response data key, there is a line 
                            --- for each value present originally, either in an array or as a scalar. 
                            select 
                                id, key, jsonb_array_elements(value) as value
                            from (
                                --- Convert all values to arrays. 
                                select 
                                    id, key,
                                    case jsonb_typeof(value)
                                        when 'array' then value
                                        else jsonb_build_array(value)
                                    end as value
                                from (
                                    --- For each Response, return one line per key in the response data JSON
                                    --- prepend the survey id to each response data key. 
                                    --- Some values are arrays, some are scalars.
                                    select 
                                        r.building_id as id,
                                        concat('s_', r.survey_id, '_', (jsonb_each(r.data)).key) as key, 
                                        (jsonb_each(r.data)).value 
                                    from responses r
                                    where r.building_id = buildings.id
                                ) as sub
                            ) as sub2
                        ) as sub3    
                        group by id, key
                    ) as sub4
                    group by id""",
                    (),
                    output_field=models.JSONField(),
                )
            ).filter(surveys_q)

        return candidates

    def is_building_in_target_pop(self, building: Building):
        return bool(self.get_target_population().filter(pk=building.id).count())

    def get_next_building_to_survey(self):
        """
        Returns a random building from the target population
        that has not been surveyed yet, or the one with the
        least amount of responses if they have all been surveyed.
        """
        buildings_w_response_counts = self.get_target_population().annotate(
            response_count=RawSQL(
                """select count(*) from responses r where r.survey_id = %s and r.building_id = buildings.id""",
                (self.id,),
                output_field=models.IntegerField(),
            )
        )

        non_surveyed_buildings = buildings_w_response_counts.filter(response_count=0)
        random_non_surveyed_pk = (
            non_surveyed_buildings.values_list("pk", flat=True).order_by("?").first()
        )

        # Check if we have results
        if random_non_surveyed_pk:
            return Building.objects.get(pk=random_non_surveyed_pk)

        # Else we'll return a random building
        return buildings_w_response_counts.order_by("?").first()

    def target_population_size(self) -> int:
        return self.get_target_population().count()

    def num_surveyed(self) -> int:
        """
        Unique buildings surveyd
        """
        return (
            Response.objects.filter(survey=self).values("building").distinct().count()
        )

    def num_responses(self) -> int:
        """
        Total number of responses. Buildings can have multiple responses.
        """
        return Response.objects.filter(survey=self).values("building").count()

    def get_progress_percent(self) -> float:
        num_candidates = self.get_target_population().count()
        if not num_candidates:
            return 0
        # We have to get unique buildings surveyed, as respondents can survey the same building
        num_surveyed = (
            Response.objects.filter(survey=self).values("building").distinct().count()
        )
        return round(num_surveyed / num_candidates * 100, 2)

    def last_n_responses(self, n: int):
        return Response.objects.filter(survey=self).order_by("-date_added")[:n]

    def map_to_qb_field(
        self, schema_field: dict, field_id: str, survey_name: str
    ) -> list[dict]:
        """
        Map between the DB schema field type and the QueryBuilder schema models
        """
        field_type = schema_field["type"]
        if field_type in ["string", "text"]:
            # For Survey string type fields, if we were given a set of possible choices
            # we'll create a querybuilder checkbox input for these.
            # In all cases, return a text input to search for arbitrary values

            qb_schemas = []

            if "options" in schema_field:
                qb_schemas.append(
                    {
                        "id": field_id,
                        "field": field_id,
                        "label": schema_field["label"]["en"],
                        "type": "string",
                        "input": "checkbox",
                        "values": [o["val"] for o in schema_field["options"]],
                        "operators": ["in", "not_in", "is_null", "is_not_null"],
                        "optgroup": survey_name,
                    },
                )

            qb_schemas.append(
                {
                    "id": field_id + "_search",
                    "field": field_id,
                    "label": schema_field["label"]["en"] + " (Search)",
                    "type": "string",
                    "input": "text",
                    "operators": [
                        "contains",
                        "not_contains",
                        "ends_with",
                        "begins_with",
                        "not_ends_with",
                        "not_begins_with",
                    ],
                    "optgroup": survey_name,
                }
            )
            return qb_schemas

        elif field_type in ["integer", "float"]:
            return [
                {
                    "id": field_id,
                    "field": field_id,
                    "label": schema_field["label"]["en"],
                    "type": field_type if field_type == "integer" else "double",
                    "input": "number",
                    "operators": [
                        "equal",
                        "not_equal",
                        "less",
                        "greater",
                        "less_or_equal",
                        "greater_or_equal",
                        "between",
                        "not_between",
                        "is_null",
                        "is_not_null",
                    ],
                    "optgroup": survey_name,
                }
            ]
        elif field_type in ["boolean", "boolean_or_null"]:
            return [
                {
                    "id": field_id,
                    "field": field_id,
                    "label": schema_field["label"]["en"],
                    "type": "boolean",
                    "input": "radio",
                    "values": ["true", "false"],
                    "operators": ["in", "is_null", "is_not_null"],
                    "optgroup": survey_name,
                }
            ]
        else:
            raise Exception(f"Unknown field type: {field_type}")

    def get_query_builder_schema(self, field_prefix: str = None):
        """
        Returns a list of query builder schema fields for the survey
        """
        qb_fields = []

        if not field_prefix:
            field_prefix = f"s_{self.id}_"

        for field_name, field_object in self.schema.items():

            field_id = f"{field_prefix}{field_name}"

            qb_field = self.map_to_qb_field(field_object, field_id, self.name)
            qb_fields.extend(qb_field)
        return qb_fields


class SurveyPopulation(models.Model):
    """
    Target population for a survey. Locked-in at survey creation time.
    Previously, we ran the expensive query on all responses at runtime.

    TODO: NOT USED YET - will optimize latency of getting the target population,
    at cost of storage, by storing the results of the query in this table.

    A decision point is whether to make these immutable at survey creation time,
    or update the target population based on new upsteam survey results.
    """

    class Meta:
        db_table = "survey_population"
        unique_together = ("survey", "building")

    survey = models.ForeignKey(Survey, on_delete=models.CASCADE)
    building = models.ForeignKey(Building, on_delete=models.CASCADE)
    date_added = models.DateTimeField("date added", default=timezone.now)


class Response(models.Model):
    """
    Response contains the answers to a Survey's questions for a Building, by a User.
    Has JSON data with an answer for each question in the survey.
    Since surveys are linked to a source dataset, has a single source dataset as well.
    """

    class Meta:
        db_table = "responses"
        unique_together = ("building", "survey", "created_by")

    data = models.JSONField()
    building = models.ForeignKey(Building, on_delete=models.CASCADE)
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    date_added = models.DateTimeField("date added", default=timezone.now)
    date_modified = models.DateTimeField("date modified", default=timezone.now)


class LatestViewData(models.Model):

    # User saved data about a building
    building = models.ForeignKey(Building, on_delete=models.CASCADE)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    date_added = models.DateTimeField("date added", default=timezone.now)
    sv_pano = models.TextField(blank=True, null=True)
    sv_heading = models.FloatField(blank=True, null=True)
    sv_pitch = models.FloatField(blank=True, null=True)
    sv_zoom = models.FloatField(blank=True, null=True)
    marker_lat = models.FloatField(blank=True, null=True)
    marker_lng = models.FloatField(blank=True, null=True)


class ProblemFlag(models.Model):
    building = models.OneToOneField(Building, on_delete=models.CASCADE)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return f"Problem with building {self.building}"


class BuildingImage(models.Model):
    """
    Using the current environment's bucket, you can retrieve the different sizes
    for the iamge by using the appropriate path
    "<tenant>/<dataset_slug>/<building_slug>/<size>/<filename>
    """

    class Meta:
        db_table = "building_images"
        unique_together = (
            "building",
            "filename",
        )

    building = models.ForeignKey(Building, on_delete=models.CASCADE)
    filename = models.TextField(null=False)
    type = models.TextField(null=False)
    date_added = models.DateTimeField("date added", default=timezone.now)
    metadata = models.JSONField(default=dict)


class DatasetOnboardingJob(models.Model):
    """
    Job to onboard a dataset.
    Contains the name of the job, the user who created it, and the date it was created.
    """

    class Meta:
        db_table = "dataset_onboarding_jobs"

    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        PROCESSING = "PROCESSING", _("Processing")
        COMPLETED = "COMPLETED", _("Completed")
        FAILED = "FAILED", _("Failed")

    name = models.TextField()
    description = models.TextField(null=True, blank=True)
    csv_file_location = models.TextField(
        null=True, blank=True, help_text="Location of the uploaded CSV file"
    )

    # Schema for dynamic attributes (unmapped columns)
    attrs_schema = models.JSONField(null=True, blank=True, default=dict)

    # Column mapping for CSV processing
    column_mapping = models.JSONField(null=True, blank=True, default=dict)

    has_coordinates = models.BooleanField(default=False)

    # Status of the job
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    # Reference to the created dataset (once processing is complete)
    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="onboarding_job",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    date_added = models.DateTimeField("date added", default=timezone.now)
    date_modified = models.DateTimeField("date modified", default=timezone.now)
