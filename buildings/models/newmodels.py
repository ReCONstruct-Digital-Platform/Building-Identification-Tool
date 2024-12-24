from django.contrib.gis.db import models
from django.db.models import JSONField
from django.utils import timezone
from autoslug import AutoSlugField


class Dataset(models.Model):
    class Meta:
        db_table = "datasets"

    # internal ID
    name = models.TextField()
    slug = AutoSlugField(populate_from='name')
    # Contains the schema of both the static and dynamic fields of 
    # the associated models. Static fields that are not present are null.
    schema = JSONField()

    date_added = models.DateTimeField("date added", default=timezone.now)
    date_modified = models.DateTimeField("date modified", default=timezone.now)



class Building(models.Model):
    """
    Base building class.
    """
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

    # Can be changed without creating a new migration
    def slugify(instance):
        fields = [instance.dataset.name, instance.address, instance.submuni, instance.muni]
        fields = [f for f in fields if f is not None]
        return " ".join(fields)
    
    # User-friendly URL slug
    slug = AutoSlugField(populate_from=slugify)

    date_added = models.DateTimeField("date added", default=timezone.now)
    date_modified = models.DateTimeField("date modified", default=timezone.now)

    def __str__(self):
        return f"Building {self.id}: {self.address}, {self.muni}, {self.postal_code}"


class Survey(models.Model):
    class Meta:
        db_table = "surveys"

    name = models.TextField()
    # Survey schema is a mapping of field_name -> (question_text, type)
    schema = JSONField()
    # Upstream dataset
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)

    # TODO: Might be able to combine data_filter and attrs_filter
    # Filter on the upstream dataset's columns
    data_filter = models.JSONField(null=True, blank=True)
    # Filter on the upstream dataset json attributes
    attrs_filter = models.JSONField(null=True, blank=True)
    # Filter on any existing survey results for the dataset
    # a mapping of survey_id -> {[survey_field]: [conditions]}
    s_filter = models.JSONField(null=True, blank=True)
