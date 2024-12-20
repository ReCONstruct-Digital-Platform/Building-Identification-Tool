from django.contrib.gis.db import models
from django.db.models import JSONField
from django.utils import timezone
from autoslug import AutoSlugField


class Dataset(models.Model):
    class Meta:
        db_table = "datasets"

    name = models.TextField()
    schema = JSONField()

    # account_id = models.TextField()

    # account_id
    # num_entries
    # date_added
    # #date_modified




class Building(models.Model):
    """
    Base building class.
    """
    class Meta:
        db_table = "buildings"

    # optional external ID field
    ext_id = models.TextField(null=True, blank=True)

    # 23 character unique ID
    lat = models.FloatField(null=True)
    lng = models.FloatField(null=True)
    point = models.PointField(null=True, spatial_index=True)

    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)

    # # If streetview imagery is available at the coordinates
    # # TODO: maybe reject all who don't have, which costs extra when onboarding
    # sv_avail = models.BooleanField(default=False)

    # # Optional geometry - like a lot polygon
    # geom = models.ForeignKey(
    #     BuildingGeometry, on_delete=models.CASCADE, null=True, blank=True
    # )

    # Have a full text search index on this
    address = models.TextField()

    # See https://developers.google.com/maps/documentation/geocoding/requests-geocoding#results
    # and https://docs.mapbox.com/api/search/geocoding/#response-forward-geocoding-with-search-text-input
    # for possible fields to be filled in
    street_name = models.TextField(null=True)
    street_num = models.TextField(null=True)
    street_num_2 = models.TextField(null=True, blank=True)

    # apt_num = models.TextField(null=True, blank=True)
    # apt_num2 = models.TextField(null=True, blank=True)

    muni = models.TextField(null=True, blank=True)

    # I think these fields should be standard to all buildings

    # submuni = models.TextField(null=True, blank=True)
    #
    # postal_code = models.TextField(null=True, blank=True)
    #
    # # construction year
    # const_year = models.SmallIntegerField()
    # num_floors = models.IntegerField(null=True, blank=True)
    # floor_area = models.FloatField(null=True, blank=True)
    # num_dwelling = models.IntegerField(null=True, blank=True)

    # JSONB field to hold an object of dynamic attributes
    attrs = models.JSONField(null=True, blank=True)


    # User-friendly URL slug
    slug = AutoSlugField(populate_from='address')


    date_added = models.DateTimeField("date added", default=timezone.now)
    date_modified = models.DateTimeField("date modified", default=timezone.now)

    # phys_link = models.TextField(null=True, blank=True)
    # const_type = models.TextField(null=True, blank=True)

    # apt_num_1 = models.TextField(null=True, blank=True)
    # apt_num_2 = models.TextField(null=True, blank=True)

    # owner_date = models.DateField(null=True, blank=True)
    # owner_type = models.TextField(null=True, blank=True)
    # owner_status = models.TextField(null=True, blank=True)

    # lot_lin_dim = models.FloatField(null=True, blank=True)
    # lot_area = models.FloatField(null=True, blank=True)


    # num_rental = models.IntegerField(null=True, blank=True)
    # num_non_res = models.IntegerField(null=True, blank=True)


    # apprais_date = models.DateField(null=True, blank=True)
    # lot_value = models.IntegerField(null=True, blank=True)
    # building_value = models.IntegerField(null=True, blank=True)
    # value = models.IntegerField(null=True, blank=True)
    # prev_value = models.IntegerField(null=True, blank=True)

    # JSON dictionary giving the IDs of any secondary objects
    # (e.g. HLMs) associated with this evaluation unit.



    def num_votes(self):
        return len(self.vote_set)

    def __str__(self):
        return f"Building {self.id}: {self.address}"


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
