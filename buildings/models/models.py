import random
import logging
from hashlib import md5

from django.conf import settings
from django.db.models.query import QuerySet
from django.utils import timezone
from django.db import connection
from django.contrib.gis.db import models
from django.db.models import Q, Count, Avg, TextField
from django.db.models.functions import Cast, Coalesce
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser, BaseUserManager
from allauth.account.adapter import DefaultAccountAdapter

from buildings.utils.constants import CUBF_TO_NAME_MAP

log = logging.getLogger(__name__)


STRING_QUERIES_TO_FILTER = {
    "q_address": "address__icontains",
    "q_locality": "locality__icontains",
    "q_region": "region__icontains",
    "q_cubf": "cubf_str__icontains",
}


SQL_RANDOM_UNVOTED_ID = f"""
    SELECT e.id FROM evalunits e 
    JOIN hlms h ON h.eval_unit_id = e.id 
    LEFT OUTER JOIN buildings_vote v ON v.eval_unit_id = e.id
    WHERE v.id is null 
    ORDER BY random() LIMIT 1;
"""

SQL_RANDOM_UNVOTED_ID_WITH_EXCLUDE = f"""
    SELECT e.id FROM evalunits e 
    JOIN hlms h ON h.eval_unit_id = e.id 
    LEFT OUTER JOIN buildings_vote v ON v.eval_unit_id = e.id
    WHERE v.id is null 
    AND e.id != %s
    ORDER BY random() LIMIT 1;
"""

# The limit parameter gives the number of eval units from which we will randomly pick
# ideally we want it somewaht large (though not too much that the query is expensive)
# but it can't be less than the number of eval units minus 1, else the query won't work
SQL_RANDOM_LEAST_VOTED_ID = f"""
    SELECT sub.id FROM 
        (SELECT e.id FROM evalunits e
        JOIN hlms h ON h.eval_unit_id = e.id 
        LEFT OUTER JOIN buildings_vote v ON (e.id = v.eval_unit_id) 
        GROUP BY e.id 
        ORDER BY COUNT(v.id) ASC LIMIT %s) 
    AS sub ORDER BY RANDOM() LIMIT 1;
"""

SQL_RANDOM_LEAST_VOTED_ID_WITH_EXCLUDE = f"""
    SELECT sub.id FROM 
        (SELECT e.id FROM evalunits e 
        JOIN hlms h ON h.eval_unit_id = e.id 
        LEFT OUTER JOIN buildings_vote v ON (e.id = v.eval_unit_id) 
        WHERE e.id != %s 
        GROUP BY e.id ORDER BY COUNT(v.id) ASC limit %s) 
    AS sub ORDER BY RANDOM() LIMIT 1;
"""

SQL_RANDOM_ID = f"""
    SELECT sub.id FROM 
        (SELECT e.id FROM evalunits e LIMIT %s) 
    AS sub ORDER BY RANDOM() LIMIT 1;
"""

SQL_RANDOM_ID_WITH_EXCLUDE = f"""
    SELECT sub.id FROM 
        (SELECT e.id FROM evalunits e 
        WHERE e.id != %s LIMIT %s) 
    AS sub ORDER BY RANDOM() LIMIT 1;
"""


class UserQuerySet(models.QuerySet):

    def get_top_n(self, n) -> QuerySet:
        return self.annotate(num_votes=Coalesce(models.Count("vote"), 0)).order_by(
            "-num_votes"
        )[:n]


class UserAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form):
        data = form.cleaned_data
        user.username = data["username"]
        user.email = data["email"]
        user.knowledge_level = data["knowledge_level"]
        user.set_password(data["password1"])
        self.populate_username(request, user)
        user.save()
        return user


class UserManager(BaseUserManager):

    def create_user(self, username, password, email=None, **otherfields):
        email = self.normalize_email(email)
        self.model(username=username, password=password, email=email, **otherfields)
        user = self.model(
            username=username,
            email=email,
            is_staff=False,
            is_active=True,
            is_superuser=False,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password, email=None, **otherfields):
        """
        Creates and saves a superuser with the given email and password.
        """
        user = self.create_user(
            username=username, password=password, email=email, **otherfields
        )
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

    def get_queryset(self) -> QuerySet:
        return UserQuerySet(self.model, using=self._db)


class User(AbstractUser):
    """https://docs.djangoproject.com/en/4.2/topics/auth/customizing/#extending-the-existing-user-model"""

    # Add any other user fields here
    knowledge_level = models.TextField(null=True, blank=True)

    objects: UserQuerySet = UserManager.from_queryset(UserQuerySet)()

    def num_votes(self):
        return len(self.vote_set.all())

    def get_avatar_url(self, size=32):
        digest = md5(self.email.encode("utf-8")).hexdigest()
        return f"https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}"

    def __str__(self):
        return str(vars(self))


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
            if op == "eq":
                lookups["num_votes"] = query["q_num_votes"]
            else:
                lookups[f"num_votes__{op}"] = query["q_num_votes"]

        log.info(lookups)
        lookups = Q(**lookups)

        # Can split up the query into multiple steps too and merge the results
        result = (
            self.annotate(num_votes=Count("vote"))
            .annotate(cubf_str=Cast("cubf", output_field=TextField()))
            .filter(lookups)
        )
        if ordering:
            result = result.order_by(ordering)

        return result

    def get_unvoted(self):
        return EvalUnit.objects.filter(vote=None)

    def get_random_unvoted_id(self, exclude_id=None):
        with connection.cursor() as cursor:
            if exclude_id:
                cursor.execute(SQL_RANDOM_UNVOTED_ID_WITH_EXCLUDE, (exclude_id,))
            else:
                cursor.execute(SQL_RANDOM_UNVOTED_ID)
            res = cursor.fetchone()

        if res is None:
            return res
        return res[0]

    def get_random_least_voted_id(self, exclude_id=None):
        # Number of least voted eval units from which to randomly pick
        # Can't be smaller than the number of units, else it won't work
        inner_limit = min(100, self.count() - 1)
        with connection.cursor() as cursor:
            if exclude_id:
                cursor.execute(
                    SQL_RANDOM_LEAST_VOTED_ID_WITH_EXCLUDE, (exclude_id, inner_limit)
                )
            else:
                cursor.execute(SQL_RANDOM_LEAST_VOTED_ID, (inner_limit,))
            res = cursor.fetchone()
        if res is None:
            return res
        # Should not be None if there is at least 1 model
        return res[0]

    def get_random_eval_unit(self, exclude_id=None):
        inner_limit = min(100, self.count() - 1)
        with connection.cursor() as cursor:
            if exclude_id:
                cursor.execute(SQL_RANDOM_ID_WITH_EXCLUDE, (exclude_id, inner_limit))
            else:
                cursor.execute(SQL_RANDOM_ID, (inner_limit,))
            res = cursor.fetchone()
        if res is None:
            return res
        # Should not be None if there is at least 1 model
        return res[0]

    def get_next_unit_to_survey(self, exclude_id=None, id_only=False):
        """
        Tries to get a random unvoted building.
        If all buildings were voted, returns a random least voted building.
        TODO: Currently modified to return only buildings with associated HLMs
        """
        id = self.get_random_unvoted_id(exclude_id=exclude_id)
        if id is None:
            id = self.get_random_least_voted_id(exclude_id=exclude_id)
        if id is None:
            id = self.get_random_eval_unit(exclude_id=exclude_id)
        if id is None:
            raise Exception("Could not get next EvalUnit!")
        if id_only:
            return id
        return EvalUnit.objects.get(pk=id)


class EvalUnitLot(models.Model):
    class Meta:
        db_table = "lots"
        indexes = [
            models.Index(fields=["id_provinc"], name="idx_id_provinc"),
        ]

    gid = models.TextField(primary_key=True)
    objectid = models.BigIntegerField(blank=True, null=True)
    co_mrc = models.TextField(blank=True, null=True)
    code_mun = models.TextField(blank=True, null=True)
    arrond = models.TextField(blank=True, null=True)
    anrole = models.TextField(blank=True, null=True)
    usag_predo = models.TextField(blank=True, null=True)
    no_lot = models.TextField(blank=True, null=True)
    nb_poly_lo = models.FloatField(blank=True, null=True)
    utilisatio = models.TextField(blank=True, null=True)
    id_provinc = models.TextField(
        null=False
    )  # reverse foreign key to lot IDs, used when populating but not when fetching thereafter
    sup_totale = models.FloatField(blank=True, null=True)
    descriptio = models.TextField(blank=True, null=True)
    nb_logemen = models.BigIntegerField(blank=True, null=True)
    nb_locaux = models.BigIntegerField(blank=True, null=True)
    shape_leng = models.FloatField(blank=True, null=True)
    shape_area = models.FloatField(blank=True, null=True)
    dat_acqui = models.DateField(blank=True, null=True)
    dat_charg = models.DateField(blank=True, null=True)
    geom = models.MultiPolygonField(null=True, spatial_index=True)


class EvalUnitManager(models.Manager):
    def get_queryset(self):
        return EvalUnitQuerySet(self.model, using=self._db)

    # .annotate(num_votes=Count('vote'))
    # .annotate(avg_score=Avg('vote__buildingtypology__score'))


class EvalUnit(models.Model):
    """
    Model representing an evaluation unit of the QC property assessment roll.
    An evaluation unit can be composed of one or more buildings, and
    has a land-use code (CUBF) describing its primary use.
    """

    # 23 character unique ID
    id = models.TextField(primary_key=True)
    lat = models.FloatField(null=True)
    lng = models.FloatField(null=True)
    point = models.PointField(null=True, spatial_index=True)
    lot = models.ForeignKey(
        EvalUnitLot, to_field="gid", on_delete=models.CASCADE, null=True, blank=True
    )
    year = models.SmallIntegerField()
    muni = models.TextField()
    muni_code = models.TextField(null=True, blank=True)
    arrond = models.TextField(null=True, blank=True)
    address = models.TextField()
    num_adr_inf = models.TextField(null=True, blank=True)
    num_adr_inf_2 = models.TextField(null=True, blank=True)
    num_adr_sup = models.TextField(null=True, blank=True)
    num_adr_sup_2 = models.TextField(null=True, blank=True)
    street_name = models.TextField(null=True, blank=True)
    apt_num = models.TextField(null=True, blank=True)
    apt_num_1 = models.TextField(null=True, blank=True)
    apt_num_2 = models.TextField(null=True, blank=True)
    mat18 = models.TextField()
    cubf = models.IntegerField()
    file_num = models.TextField(null=True, blank=True)
    nghbr_unit = models.TextField(null=True, blank=True)
    owner_date = models.DateField(null=True, blank=True)
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
    apprais_date = models.DateField(null=True, blank=True)
    lot_value = models.IntegerField(null=True, blank=True)
    building_value = models.IntegerField(null=True, blank=True)
    value = models.IntegerField(null=True, blank=True)
    prev_value = models.IntegerField(null=True, blank=True)
    # JSON dictionary giving the IDs of any secondary objects
    # (e.g. HLMs) associated with this evaluation unit.
    associated = models.JSONField(null=True, blank=True)
    date_added = models.DateTimeField("date added", default=timezone.now)

    # Override the objects attribute of the model
    # in order to implement custom search functionality
    objects = EvalUnitManager.from_queryset(EvalUnitQuerySet)()

    class Meta:
        db_table = "evalunits"

    def num_votes(self):
        return len(self.vote_set)

    def cubf_name(self):
        if self.cubf in CUBF_TO_NAME_MAP:
            return CUBF_TO_NAME_MAP[self.cubf]
        else:
            return ""

    def __str__(self):
        return f"{self.address}, {self.muni}, CUBF: {self.cubf_name()}"

    @classmethod
    def get_field_names(self):
        return [f.name for f in EvalUnit._meta.get_fields()]

    @classmethod
    def _get_proper_field_name(self, field):
        if field in [None, "None"]:
            return "address"

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
            return "address"

    @classmethod
    def get_ordering(cls, order_by, direction):

        ordering = cls._get_proper_field_name(order_by)

        if direction in [None, "None"]:
            direction = "desc"

        if direction == "desc":
            ordering = f"-{ordering}"

        return ordering, direction


class EvalUnitLatestViewDataQuerySet(models.QuerySet):

    def get_latest_view_data(self, unit_id, user_id):

        # First look if there are any previous saved data for this building
        if self.filter(eval_unit_id=unit_id).count() == 0:
            return None

        # Then check if there is a previous saved value for this user
        # If not, return the latest view saved by any other user
        if self.filter(eval_unit_id=unit_id, user_id=user_id).count() == 0:
            return self.filter(eval_unit_id=unit_id).order_by("-date_added").first()
        else:
            return (
                self.filter(eval_unit_id=unit_id, user_id=user_id)
                .order_by("-date_added")
                .first()
            )


class EvalUnitLatestViewData(models.Model):

    # User saved data about a building
    eval_unit = models.ForeignKey(EvalUnit, on_delete=models.CASCADE)
    user = models.ForeignKey(
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

    objects = EvalUnitLatestViewDataQuerySet.as_manager()


class VoteQuerySet(models.QuerySet):
    def get_latest(self, n=10):
        return self.order_by("-date_added")[:n]


class Vote(models.Model):
    """
    Votes link submitted data (surveys, nobuildingflags or other)
    to a specific building and user.
    Submitted data implements a 1-to-1 relationship to a Vote.
    """

    eval_unit = models.ForeignKey(EvalUnit, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date_added = models.DateTimeField("date added", auto_now_add=True)
    date_modified = models.DateTimeField("date modified", auto_now=True)

    objects = VoteQuerySet.as_manager()

    def __str__(self):
        return f"{self.user.username} voted on {self.eval_unit.address} on {self.date_added}"


class NoBuildingFlag(models.Model):
    vote = models.OneToOneField(Vote, on_delete=models.CASCADE)

    def __str__(self):
        return f"No building at {self.vote.eval_unit.address}"


class EvalUnitStreetViewImage(models.Model):
    eval_unit = models.ForeignKey(EvalUnit, on_delete=models.CASCADE)
    uuid = models.TextField(null=False)
    date_added = models.DateTimeField("date added", default=timezone.now)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )


class EvalUnitSatelliteImage(models.Model):
    eval_unit = models.ForeignKey(EvalUnit, on_delete=models.CASCADE)
    uuid = models.TextField(null=False)
    date_added = models.DateTimeField("date added", default=timezone.now)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )


class HLMBuilding(models.Model):
    """
    Model representing an HLM building.
    The data was obtained after a freedom of information type request to the SHQ
    and is saved here https://f005.backblazeb2.com/file/bit-data-public/hlms.csv
    """

    class Meta:
        db_table = "hlms"

    id = models.IntegerField(primary_key=True)
    lat = models.FloatField(null=True)
    lng = models.FloatField(null=True)
    point = models.PointField(null=True)
    eval_unit = models.ForeignKey(EvalUnit, on_delete=models.CASCADE)
    streetview_available = models.BooleanField(null=True)
    project_id = models.IntegerField()
    organism = models.TextField()
    service_center = models.TextField()
    address = models.TextField(null=True)
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
    interest_adjust_date = models.DateField(null=True, blank=True)
    contract_end_date = models.DateField(null=True, blank=True)
    category = models.TextField()
    building_id = models.IntegerField()

    @classmethod
    def get_disrepair_state(cls, ivp):
        if ivp <= 5:
            return "A"
        elif ivp <= 10:
            return "B"
        elif ivp <= 15:
            return "C"
        elif ivp <= 30.2:
            return "D"
        else:
            return "E"


class UploadImageJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        IN_PROGRESS = "in_progress", _("In Progress")
        DONE = "done", _("Done")
        ERROR = "error", _("Error")

    """Async job for uploading screenshots to storage"""
    eval_unit = models.ForeignKey(EvalUnit, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date_added = models.DateTimeField("date added", default=timezone.now)
    status = models.TextField(choices=Status.choices, default=Status.PENDING)
    job_data = models.JSONField()

    def __str__(self):
        return f"Job {self.id}: {self.status}"
