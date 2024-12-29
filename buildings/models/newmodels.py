from django.conf import settings
from django.contrib.gis.db import models
from django.db.models import JSONField
from django.utils import timezone
from autoslug import AutoSlugField


class Dataset(models.Model):
    class Meta:
        db_table = "datasets"

    name = models.TextField()
    description = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    slug = AutoSlugField(populate_from='name')
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
        fields = [instance.dataset.name, instance.address, instance.submuni, instance.muni]
        fields = [f for f in fields if f is not None]
        return " ".join(fields)
    
    class Meta:
        db_table = "buildings"
        unique_together = ('ext_id', 'lat', 'lng', 'address', 'muni')

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
        unique_together = ("name", "dataset", "schema", "dataset_filter", "surveys_filter")

    name = models.TextField()
    description = models.TextField()
    slug = AutoSlugField(populate_from='name')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    def get_target_population():
        q_buildings = None
        q_responses = None
        Building.objects.filter(
         
        )
        pass

    # Source dataset
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)

    # Filter on the upstream dataset's columns and json attributes
    # JSON necessary to construct a Q object on the source dataset
    dataset_filter = models.JSONField(null=True, blank=True)

    # Survey schema is a mapping of field_id -> (field_label, type, question_text, widget)
    schema = JSONField()

    # Filter on any existing survey results for the dataset
    # a mapping of survey_id -> {[survey_field]: [conditions]}
    surveys_filter = models.JSONField(null=True, blank=True)

    date_added = models.DateTimeField("date added", default=timezone.now)
    date_modified = models.DateTimeField("date modified", default=timezone.now)


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
    building = models.ForeignKey(
        Building,
        on_delete=models.CASCADE
    )
    survey = models.ForeignKey(
        Survey,
        on_delete=models.CASCADE
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    date_added = models.DateTimeField("date added", default=timezone.now)
    date_modified = models.DateTimeField("date modified", default=timezone.now)
