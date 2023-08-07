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
    "q_address": "address__icontains",
    "q_locality": "locality__icontains",
    "q_region": "region__icontains",
    "q_cubf": "cubf_str__icontains",
}

class Profile(models.Model):

    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)
    
    def get_avatar_url(self, size=32):
        digest = md5(self.user.email.encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'
    

class EvalUnitQuerySet(models.QuerySet):
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

        # if "q_score" in query:
        #     op = query["q_score_op"]
        #     if op == 'eq':
        #         lookups["avg_score"] = query["q_score"]
        #     else:
        #         lookups[f"avg_score__{op}"] = query["q_score"]

        log.info(lookups)
        lookups = Q(**lookups) 

        # Can split up the query into multiple steps too and merge the results
        result = self.annotate(num_votes=Count('vote')) \
                    .annotate(cubf_str=Cast('cubf', output_field=TextField())) \
                    .filter(lookups)
        if ordering:
            result = result.order_by(ordering)

        return result
    
    def get_unvoted(self):
        return EvalUnit.objects.filter(vote = None)
    
    def get_random_unvoted(self, exclude_id=None):
        # "order_by('?')" orders objects randomly in the database.
        return self.get_unvoted().exclude(id=exclude_id).order_by('?').first()
    
    def get_random_least_voted(self, exclude_id=None, num_buildings_to_pick_from=25):
        # Get the 'num_buildings_to_pick_from' least voted buildings 
        least_voted_buildings = EvalUnit.objects.exclude(id=exclude_id) \
                .annotate(num_votes=Count('vote')) \
                .order_by('-num_votes')[:num_buildings_to_pick_from]
        
        if len(least_voted_buildings) == 0:
            return EvalUnit(id=0)
            
        # return a random one from them
        rand_num = random.randint(1, num_buildings_to_pick_from)
        return least_voted_buildings[rand_num]
    
    def get_next_unit_to_survey(self, exclude_id=None):
        """
        Tries to get a random unvoted building. 
        If all buildings were voted, returns a random least voted building.
        """
        import code
        code.interact(local=dict(globals(), **locals()))
        b = self.get_random_unvoted(exclude_id=exclude_id)
        if b is None:
            b = self.get_random_least_voted(exclude_id=exclude_id)
        return b
    


    
class EvalUnitManager(models.Manager):
    def get_queryset(self):
        return EvalUnitQuerySet(self.model, using=self._db).annotate(num_votes=Count('vote'))
        # .annotate(avg_score=Avg('vote__buildingtypology__score'))


class EvalUnit(models.Model):
    """
    Model representing an evaluation unit of the QC property assessment roll.
    An evaluation unit can be composed of one or more buildings, and
    has a primary land-use code (CUBF) describing its primary use.
    """
    # 23 character unique ID
    id = models.TextField(primary_key=True)
    lat = models.FloatField()
    lng = models.FloatField()
    muni = models.TextField()
    muni_code = models.TextField(null=True, blank=True)
    arrond = models.TextField(null=True, blank=True)
    address = models.TextField()
    num_adr_inf = models.TextField(null=True, blank=True)
    num_adr_inf_2 = models.TextField(null=True, blank=True)
    num_adr_sup = models.TextField(null=True, blank=True)
    num_adr_sup_2 = models.TextField(null=True, blank=True)
    way_type = models.TextField(null=True, blank=True)
    way_link = models.TextField(null=True, blank=True)
    street_name = models.TextField(null=True, blank=True)
    cardinal_pt = models.TextField(null=True, blank=True)
    apt_num = models.TextField(null=True, blank=True)
    apt_num_1 = models.TextField(null=True, blank=True)
    apt_num_2 = models.TextField(null=True, blank=True)
    mat18 = models.TextField()
    cubf = models.IntegerField()
    file_num = models.TextField(null=True, blank=True)
    nghbr_unit = models.TextField(null=True, blank=True)
    owner_date = models.DateTimeField(null=True, blank=True)
    owner_type = models.TextField(null=True, blank=True)
    owner_status = models.TextField(null=True, blank=True)
    lot_lin_dim = models.FloatField(null=True, blank=True)
    lot_area = models.FloatField(null=True, blank=True)
    max_floors = models.IntegerField(null=True, blank=True)
    const_yr = models.IntegerField(null=True, blank=True)
    const_yr_real = models.TextField(null=True, blank=True)
    floor_area = models.FloatField(null=True, blank=True)
    phys_link = models.TextField(null=True, blank=True)
    const_type = models.TextField(null=True, blank=True)
    num_dwelling = models.IntegerField(null=True, blank=True)
    num_rental = models.IntegerField(null=True, blank=True)
    num_non_res = models.IntegerField(null=True, blank=True)
    apprais_date = models.DateTimeField(null=True, blank=True)
    lot_value = models.IntegerField(null=True, blank=True)
    building_value = models.IntegerField(null=True, blank=True)
    value = models.IntegerField(null=True, blank=True)
    prev_value = models.IntegerField(null=True, blank=True)

    # JSON dictionary giving the IDs of any secondary objects 
    # (e.g. HLMs) associated with this evaluation unit.
    associated = models.JSONField(null=True, blank=True)
    date_added = models.DateTimeField('date added', default=timezone.now)

    # Override the objects attribute of the model
    # in order to implement custom search functionality
    objects = EvalUnitManager.from_queryset(EvalUnitQuerySet)()


    def num_votes(self):
        return len(self.vote_set)
    
    def cubf_name(self):
        if self.cubf in CUBF_TO_NAME_MAP:
            return CUBF_TO_NAME_MAP[self.cubf]
        else:
            return ''
        
    # def avg_score(self):
    #     if self.vote_set is None or self.vote_set.filter(buildingtypology__isnull=False).count() == 0:
    #         return 0
        
    #     acc = 0
    #     n = 0
    #     for vote in self.vote_set.filter(buildingtypology__isnull=False):
    #         acc += vote.buildingtypology.score
    #         n += 1

    #     return round(acc/n, 2)
        

    def __str__(self):
        return f'{self.address} ({self.lat}, {self.lng})'
    
    @classmethod
    def get_field_names(self):
        return [f.name for f in EvalUnit._meta.get_fields()]

    @classmethod
    def _get_proper_field_name(self, field):
        if field in [None, 'None']:
            return "num_votes"
        
        field = field.lower()
        if field == "address":
            return "address"
        if field == "num_votes":
            return field
        elif field in self.get_field_names():
            return field
        # elif field == 'score':
        #     return 'avg_score'
        else:
            # If the field is not valid, default to address
            return "num_votes"

    @classmethod
    def get_ordering(cls, order_by, direction):

        ordering = cls._get_proper_field_name(order_by)

        if direction in [None, 'None']:
            direction = "desc"

        if direction == 'desc':
            ordering = f'-{ordering}'

        return ordering, direction


class EvalUnitLatestViewDataQuerySet(models.QuerySet):

    def get_latest_view_data(self, unit_id, user_id):

        # First look if there are any previous saved data for this building
        if self.filter(building_id = unit_id).count() == 0:
            return None
        
        # Then check if there is a previous saved value for this user
        # If not, return the latest view saved by any other user
        if self.filter(building_id = unit_id, user_id = user_id).count() == 0:
            return self.filter(building_id = unit_id).order_by('-date_added').first()
        else:
            return self.filter(building_id = unit_id, user_id = user_id).order_by('-date_added').first()

class EvalUnitLatestViewData(models.Model):

    # User saved data about a building
    eval_unit = models.ForeignKey(EvalUnit, on_delete=models.CASCADE)
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

    objects = EvalUnitLatestViewDataQuerySet.as_manager()


class VoteQuerySet(models.QuerySet):
    def get_latest(self, n=10):
        return self.order_by('-date_added')[:n]
    

class Vote(models.Model):
    """
    Votes link submitted data (surveys, nobuildingflags or other) 
    to a specific building and user.
    Submitted data implements a 1-to-1 relationship to a Vote.
    """
    eval_unit = models.ForeignKey(EvalUnit, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    date_added = models.DateTimeField('date added', auto_now_add=True)
    data_modified  = models.DateTimeField('date modified', auto_now=True)

    objects = VoteQuerySet.as_manager()
    def __str__(self):
        return f'{self.user.username} voted on {self.eval_unit.address} on {self.date_added}'


class NoBuildingFlag(models.Model):
    vote = models.OneToOneField(Vote, on_delete=models.CASCADE)

    def __str__(self):
        return f'No building at {self.vote.eval_unit.address}'
    

class EvalUnitStreetViewImage(models.Model):
    eval_unit = models.ForeignKey(EvalUnit, on_delete=models.CASCADE)
    uuid = models.TextField(null=False)
    date_added = models.DateTimeField('date added', default=timezone.now)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

class EvalUnitSatelliteImage(models.Model):
    eval_unit = models.ForeignKey(EvalUnit, on_delete=models.CASCADE)
    uuid = models.TextField(null=False)
    date_added = models.DateTimeField('date added', default=timezone.now)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )


class HLMBuilding(models.Model):
    """
    Model representing an HLM building.
    """
    id = models.IntegerField(primary_key=True)
    eval_unit = models.ForeignKey(EvalUnit, on_delete=models.CASCADE)
    project_id = models.IntegerField()
    organism = models.TextField()
    service_center = models.TextField()
    street_num = models.TextField()
    street_name = models.TextField()
    muni = models.TextField()
    postal_code = models.TextField()
    num_dwellings = models.IntegerField()
    num_floors = models.IntegerField()
    area_footprint = models.FloatField()
    area_total = models.FloatField()
    ivp = models.FloatField()
    disrepair_state = models.TextField()
    interest_adjust_date = models.DateTimeField(null=True, blank=True)
    contract_end_date = models.DateTimeField(null=True, blank=True)
    category = models.TextField()
    building_id = models.IntegerField()

