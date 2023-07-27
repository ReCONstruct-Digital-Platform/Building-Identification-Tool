from hashlib import md5
import random

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Q, Count, Avg, TextField
from django.db.models.functions import Cast, Coalesce
from django.utils.translation import gettext_lazy as _
import logging

from buildings.utils.contants import CUBF_TO_NAME_MAP

log = logging.getLogger(__name__)


STRING_QUERIES_TO_FILTER = {
    "q_address": "formatted_address__icontains",
    "q_locality": "locality__icontains",
    "q_region": "region__icontains",
    "q_cubf": "cubf_str__icontains",
}


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)
    
    def get_avatar_url(self, size=32):
        digest = md5(self.user.email.encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'
    

class BuildingQuerySet(models.QuerySet):
    # We implement this ourselves, not an override of a QuerySet method
    def search(self, query=None, ordering=None):
        if query is None or len(query) == 0:
            if ordering:
                return self.all().order_by(ordering)
            else:
                return self.all()
        
        # Use this to filter on CUBF as a string
        # .annotate(cubf_str=Cast('cubf', output_field=TextField()))
        
        lookups = {}

        # Add all string field queries to lookups if present
        for key, q_filter in STRING_QUERIES_TO_FILTER.items():
            if key in query:
                lookups[q_filter] = query[key]

        # Validation in the view ensures num_votes is always accompagnied by an op
        if "q_num_votes" in query:
            op = query["q_num_votes_op"]
            # For equals queries, we don't need to do anything to the filter
            if op == 'eq':
                lookups["num_votes"] = query["q_num_votes"]
            else:
                lookups[f"num_votes__{op}"] = query["q_num_votes"]

        if "q_score" in query:
            op = query["q_score_op"]
            if op == 'eq':
                lookups["avg_score"] = query["q_score"]
            else:
                lookups[f"avg_score__{op}"] = query["q_score"]

        log.info(lookups)
        lookups = Q(**lookups) 

        # Can split up the query into multiple steps too and merge the results
        result = self.annotate(num_votes=Count('vote')) \
                    .annotate(avg_score=Coalesce(Avg('vote__buildingtypology__score'), 0.0)) \
                    .annotate(cubf_str=Cast('cubf', output_field=TextField())) \
                    .filter(lookups)
        if ordering:
            result = result.order_by(ordering)

        return result
    
    def get_unvoted(self):
        return Building.objects.filter(vote = None)
    
    def get_random_unvoted(self, exclude_id=None):
        # "order_by('?')" orders objects randomly in the database.
        return self.get_unvoted().exclude(id=exclude_id).order_by('?').first()
    
    def get_random_least_voted(self, exclude_id=None, num_buildings_to_pick_from=25):
        # Get the 'num_buildings_to_pick_from' least voted buildings 
        least_voted_buildings = Building.objects.exclude(id=exclude_id) \
                .annotate(num_votes=Count('vote')) \
                .order_by('-num_votes')[:num_buildings_to_pick_from]
        
        if len(least_voted_buildings) == 0:
            return Building(id=0)
            
        # return a random one from them
        rand_num = random.randint(1, num_buildings_to_pick_from)
        return least_voted_buildings[rand_num]
    
    def get_next_building_to_classify(self, exclude_id=None):
        """
        Tries to get a random unvoted building. 
        If all buildings were voted, returns a random least voted building.
        """
        b = self.get_random_unvoted(exclude_id=exclude_id)
        if b is None:
            b = self.get_random_least_voted(exclude_id=exclude_id)
        return b
    


    
class BuildingManager(models.Manager):
    def get_queryset(self):
        return BuildingQuerySet(self.model, using=self._db).annotate(num_votes=Count('vote')).annotate(avg_score=Avg('vote__buildingtypology__score'))


class Building(models.Model):
    street_number = models.TextField()
    street_name = models.TextField()
    locality = models.TextField(blank=True, null=True)
    region = models.TextField()
    province = models.TextField()
    country = models.TextField()
    postal_code = models.CharField(max_length=7)
    formatted_address = models.TextField()
    cubf = models.IntegerField()
    lat = models.FloatField()
    lon = models.FloatField()
    date_added = models.DateTimeField('date added', default=timezone.now)

    # Original address in the CSV
    csv_address = models.TextField(blank=True, null=True)
    
    # Set as text field as some were bigger than the maximum integer allowed by SQLite!
    serial_number = models.TextField(blank=True, null=True, unique=True)

    # Linear dimension of the land facing the public right of way
    lin_dim = models.FloatField(blank=True, null=True)

    # Area of the land entered in the roll
    area = models.FloatField(blank=True, null=True)

    # Maximum number of floors in the buildings of the assessment unit
    max_num_floor = models.IntegerField(blank=True, null=True)

    # Year of the original construction of the main building, if there is only one
    construction_year = models.IntegerField(blank=True, null=True)

    # Indication of whether the original year of construction indicated is real or estimated
    year_real_esti = models.CharField(max_length=1, blank=True, null=True)

    # Floor area of the main building, if there is only one
    floor_area = models.FloatField(blank=True, null=True)

    type_const = models.IntegerField(blank=True, null=True)

    # Total number of dwellings in the assessment unit
    num_dwell = models.IntegerField(blank=True, null=True)

    # Total number of rental rooms in the assessment unit
    num_rental = models.IntegerField(blank=True, null=True)

    # Total number of non-residential premises in the assessment unit
    num_non_res = models.IntegerField(blank=True, null=True)

    # Value of the property entered on the current roll
    value_prop = models.IntegerField(blank=True, null=True)

    # Used in the google places API to retrieve photos, etc.
    place_id = models.TextField(blank=True, null=True)


    # Override the objects attribute of the model
    # in order to implement custom search functionality
    # objects = BuildingQuerySet.as_manager()
    objects = BuildingManager.from_queryset(BuildingQuerySet)()


    def num_votes(self):
        return len(self.vote_set)
    
    def cubf_name(self):
        if self.cubf in CUBF_TO_NAME_MAP:
            return CUBF_TO_NAME_MAP[self.cubf]
        else:
            return ''
        
    def avg_score(self):
        """
        Only the building typology vote score for now

        b.vote_set.aggregate(Avg('buildingtypology__score'))
        Building.objects.filter(vote__buildingtypology__score__gt=4).aggregate(django.db.models.Avg('vote__buildingtypology__score')

        """
        if self.vote_set is None or self.vote_set.filter(buildingtypology__isnull=False).count() == 0:
            return 0
        
        acc = 0
        n = 0
        for vote in self.vote_set.filter(buildingtypology__isnull=False):
            acc += vote.buildingtypology.score
            n += 1

        return round(acc/n, 2)
        

    def __str__(self):
        return f'{self.formatted_address} {self.region} ({self.lat}, {self.lon})'
    
    @classmethod
    def get_field_names(self):
        return [f.name for f in Building._meta.get_fields()]

    @classmethod
    def _get_proper_field_name(self, field):
        if field in [None, 'None']:
            return "avg_score"
        
        field = field.lower()
        if field == "address":
            return "formatted_address"
        if field == "num_votes":
            return field
        elif field in self.get_field_names():
            return field
        elif field == 'score':
            return 'avg_score'
        else:
            # If the field is not valid, default to id
            return "avg_score"

    @classmethod
    def get_ordering(cls, order_by, direction):

        ordering = cls._get_proper_field_name(order_by)

        if direction in [None, 'None']:
            direction = "desc"

        if direction == 'desc':
            ordering = f'-{ordering}'

        return ordering, direction


class BuildingLatestViewDataQuerySet(models.QuerySet):

    def get_latest_view_data(self, building_id, user_id):
        print(f'Looking for past saved data for building {building_id}')

        # First look if there are any previous saved data for this building
        if self.filter(building_id = building_id).count() == 0:
            return None
        
        if self.filter(building_id = building_id, user_id = user_id).count() == 0:
            print(self.filter(building_id = building_id).all())
            return self.filter(building_id = building_id).order_by('-date_added').first()
        
        else:
            return self.filter(building_id = building_id, user_id = user_id).order_by('-date_added').first()

class BuildingLatestViewData(models.Model):

    # User saved data about a building
    building = models.ForeignKey(Building, on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    date_added = models.DateTimeField('date added', default=timezone.now)

    sv_pano = models.TextField(blank=True, null=True)

    sv_heading = models.FloatField(blank=True, null=True)
    sv_pitch = models.FloatField(blank=True, null=True)
    sv_zoom = models.FloatField(blank=True, null=True)
    marker_lat = models.FloatField(blank=True, null=True)
    marker_lng = models.FloatField(blank=True, null=True)

    objects = BuildingLatestViewDataQuerySet.as_manager()


class Material(models.Model):
    name = models.CharField(max_length=50, unique=True)
    date_added = models.DateTimeField('date added', default=timezone.now)

    def __str__(self):
        return f'{self.name}'


class VoteQuerySet(models.QuerySet):
    
    def get_latest(self, n=10):
        return self.order_by('-date_added')[:n]
    

class Vote(models.Model):
    building = models.ForeignKey(Building, on_delete=models.CASCADE)
    date_added = models.DateTimeField('date added', default=timezone.now)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    objects = VoteQuerySet.as_manager()

    def __str__(self):
        return f'{self.user.username} voted on {self.building.formatted_address} on {self.date_added}'


class MaterialScore(models.Model):
    vote = models.ForeignKey(Vote, on_delete=models.CASCADE)
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)

    def __str__(self):
        return f'{self.material} score of {self.score}'
    

class NoBuildingFlag(models.Model):
    vote = models.OneToOneField(Vote, on_delete=models.CASCADE)

    def __str__(self):
        return f'No building at {self.vote.building.formatted_address}'
    
class BuildingNote(models.Model):
    vote = models.OneToOneField(Vote, null=True, on_delete=models.CASCADE)
    note = models.TextField(default=None, blank=True, null=True)

    def __str__(self):
        return f'{self.id} {self.vote.user} said on building {self.vote.building.id}: {self.note}'
    

class Typology(models.Model):
    name = models.CharField(max_length=150)
    date_added = models.DateTimeField('date added', default=timezone.now)

    def __str__(self):
        return f'{self.name}'
    
class BuildingTypology(models.Model):
    vote = models.OneToOneField(Vote, on_delete=models.CASCADE)
    typology = models.ForeignKey(Typology, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)

    def __str__(self):
        return f'{self.vote}'
    

class BuildingStreetViewImage(models.Model):
    building = models.ForeignKey(Building, on_delete=models.CASCADE)
    uuid = models.TextField(null=False)
    date_added = models.DateTimeField('date added', default=timezone.now)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

class BuildingSatelliteImage(models.Model):
    building = models.ForeignKey(Building, on_delete=models.CASCADE)
    uuid = models.TextField(null=False)
    date_added = models.DateTimeField('date added', default=timezone.now)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )


