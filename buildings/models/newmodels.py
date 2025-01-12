import random
from django.conf import settings
from django.contrib.gis.db import models
from django.db.models import JSONField
from django.utils import timezone
from autoslug import AutoSlugField

from django.db.models import Q
from django.db.models.expressions import RawSQL
from django.utils.translation import gettext_lazy as _

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

    date_added = models.DateTimeField("date added", default=timezone.now)
    date_modified = models.DateTimeField("date modified", default=timezone.now)


class Building(models.Model):
    """
    Base building class.
    The objects of Surveys.
    """

    # Can be changed without creating a new migration
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

    # 23 character unique ID
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

    # # construction year
    const_year = models.SmallIntegerField(null=True, blank=True)
    num_floors = models.IntegerField(null=True, blank=True)
    floor_area = models.FloatField(null=True, blank=True)

    # JSONB field to hold an object of dynamic attributes
    attrs = models.JSONField(null=True, blank=True)

    # User-friendly URL slug
    slug = AutoSlugField(populate_from=slugify)

    date_added = models.DateTimeField("date added", default=timezone.now)
    date_modified = models.DateTimeField("date modified", default=timezone.now)

    def __str__(self):
        return f"Building {self.id}: {self.address}, {self.muni}, {self.postal_code}"


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
        CREATED = "CREATED", _("Created")
        ACTIVE = "ACTIVE", _("Active")
        COMPLETED = "COMPLETED", _("Completed")
        ARCHIVED = "ARCHIVED", _("Archived")

    status = models.TextField(choices=Status.choices, default=Status.CREATED)

    name = models.TextField()
    description = models.TextField(null=True, blank=True)
    slug = AutoSlugField(populate_from="name")

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    # Source dataset
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)

    # Filter on the upstream dataset's columns and json attributes
    # JSON necessary to construct a Q object on the source dataset
    # Can be fed to Q to create an ORM filter
    dataset_filter = models.JSONField(null=True, blank=True)

    # Survey schema is a mapping of field_id -> (field_label, type, question_text, widget)
    schema = JSONField()

    # Holds modal HTML
    modals = JSONField(null=True, blank=True)

    # Filter on any existing survey results for the dataset
    # a mapping of survey_id -> {[survey_field]: [conditions]}
    # Can be fed to Q to create an ORM filter
    surveys_filter = models.JSONField(null=True, blank=True)

    date_added = models.DateTimeField("date added", default=timezone.now)
    date_modified = models.DateTimeField("date modified", default=timezone.now)

    # If this gets slow, implement a view for the target population
    # mapping building_id -> aggregated response data
    # IT will have to refresh everytime a new response is added
    # https://www.fusionbox.com/blog/detail/using-materialized-views-to-implement-efficient-reports-in-django/643/
    # https://pypi.org/project/django-db-views/
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
                    """select jsonb_object_agg(key, value)
                        from (
                            select 
                                id, key, jsonb_agg(distinct value) as value
                            from (
                                select 
                                    id, key, jsonb_array_elements(value) as value
                                from (
                                    --- Collect all responses in a survey in jsonb arrays 
                                    select 
                                        id, key,
                                        case jsonb_typeof(value)
                                            when 'array' then value
                                            else jsonb_build_array(value)
                                        end as value
                                    from (
                                        --- For each building, explode response data
                                        --- prepend the survey id to each response data key
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

        # Else we'll return a building with the least amount of responses
        return buildings_w_response_counts.order_by("response_count").first()

    def get_completion_status(self):
        num_candidate_buildings = self.get_target_population().count()
        # We have to get unique buildings surveyed, as respondents can survey the same building
        num_buildings_surveyed = (
            Response.objects.filter(survey=self).values("building").distinct().count()
        )
        return num_buildings_surveyed / num_candidate_buildings

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
                        "values": list(schema_field["options"].keys()),
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

        elif field_type in ["integer"]:
            return [
                {
                    "id": field_id,
                    "field": field_id,
                    "label": schema_field["label"]["en"],
                    "type": "integer",
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
        elif field_type in ["boolean"]:
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

    def get_query_builder_schema(self):
        """
        Returns a list of query builder schema fields for the survey
        """
        qb_fields = []
        for field_name, field_object in self.schema.items():

            field_id = f"s_{self.id}_{field_name}"

            qb_field = self.map_to_qb_field(field_object, field_id, self.name)
            qb_fields.extend(qb_field)
        return qb_fields


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
