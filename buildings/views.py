import git
import json
import requests
import traceback

import IPython
from pprint import pprint
from datetime import datetime
from ipaddress import ip_address, ip_network
from render_block import render_block_to_string
from django.db import connection
from django.views import generic 
from django.conf import settings
from django.db import transaction
from django.contrib import messages 
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Sum
from django.db.models.functions import Round
from django.forms.models import model_to_dict
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST   
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404, render, redirect
from buildings.utils.constants import CUBF_TO_NAME_MAP
from buildings.utils.utility import print_query_dict, verify_github_signature
from django.contrib.gis.db.models.functions import AsGeoJSON
from django.core.serializers import serialize

from .forms import CreateUserForm
from .models.surveys import SurveyV1Form
from config.settings import WEBHOOK_SECRET, BASE_DIR
from .models.models import (
    EvalUnit, EvalUnitLatestViewData, HLMBuilding, NoBuildingFlag, UploadImageJob, User, Vote
)
import logging

log = logging.getLogger(__name__)

@login_required(login_url='buildings:login')
def index(request):
    template = 'buildings/index.html'

    total_votes = Vote.objects.count() or 1
    latest_votes = Vote.objects.order_by('-date_modified').all()

    num_user_votes = Vote.objects.filter(user = request.user).count()
    user_votes = Vote.objects.filter(user = request.user).order_by('-date_modified').all()

    top_3_users = User.objects.get_top_n(3)
    top_3_total_votes = sum(t.num_votes for t in top_3_users)
    top_3_vote_percentage = int(top_3_total_votes / total_votes * 100)

    page_num_latest = request.GET.get('latest_votes_page', 1)
    page_num_user = request.GET.get('user_votes_page', 1)
    latest_votes_page = Paginator(latest_votes, 10).get_page(page_num_latest)
    user_votes_page = Paginator(user_votes, 10).get_page(page_num_user)
    active_tab = request.GET.get('active_tab', 'leaderboard')

    context = {
        "total_votes": total_votes,
        "num_user_votes": num_user_votes,
        "latest_votes_page": latest_votes_page,
        "user_votes_page": user_votes_page,
        "active_tab": active_tab,
        "top_3_users": top_3_users,
        "top_3_total_votes": top_3_total_votes,
        "top_3_vote_percentage": top_3_vote_percentage
    }

    if request.htmx:
        rendered_content = render_block_to_string(
            template, "activity-tab-content", context=context, request=request
        )
    else:
        rendered_content = render(request, template, context)

    return HttpResponse(content=rendered_content)


def _get_current_html_query_str(query):
    if len(query) == 0:
        return ''
    curr_query = ""

    if "order_by" in query:
        del query["order_by"]
    if "dir" in query:
        del query["dir"]

    for k, v in query.items():
        curr_query += f"&{k}={v}"
    return curr_query


def _populate_query(request):
    query = {}
    for k, v in request.GET.items():
        if v and v != '':
            query[k] = v
    return query


def _validate_query(query):
    if "q_num_votes" in query and "q_num_votes_op" not in query:
         query["q_num_votes_op"] = "gte"

    elif "q_num_votes_op" in query and "q_num_votes" not in query:
        del query["q_num_votes_op"]

    return query


@login_required(login_url='buildings:login')
def all_buildings(request):
    # Get all the query elements and assemble them in a query dictionary
    query = _populate_query(request)
    query = _validate_query(query)
    log.info(f'Query: {query}')

    order_by = request.GET.get('order_by')
    dir = request.GET.get('dir')

    ordering, direction = EvalUnit.get_ordering(order_by, dir)
    log.debug(f'Ordering: {ordering}, direction: {direction}')
    qs = EvalUnit.objects.search(query=query, ordering=ordering)

    paginator = Paginator(qs, 25) # Show 25 contacts per page.

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    current_search_query = _get_current_html_query_str(query)

    context = {
        "page_obj": page_obj,
        "order_by": order_by,
        "dir": direction,
        "current_search_query": current_search_query
    }
    template = 'buildings/all_buildings.html'
    
    if request.htmx:
        template = 'buildings/partials/all_buildings.html'

    return render(request, template, context)



@login_required(login_url='buildings:login')
def survey(_):
    random_unscored_unit = EvalUnit.objects.get_next_unit_to_survey()
    eval_unit_id = random_unscored_unit.id
    return redirect('buildings:survey_v1', eval_unit_id=eval_unit_id)


@login_required(login_url='buildings:login')
def survey_v1(request, eval_unit_id):

    eval_unit = get_object_or_404(EvalUnit, pk=eval_unit_id)

    hlms = None
    hlm_info = None
    avg_disrepair = None

    # if eval_unit.associated is not None and 'hlm' in eval_unit.associated:
    hlms = HLMBuilding.objects.filter(eval_unit=eval_unit).order_by('street_num')
    if len(hlms) > 0:
        hlm_info = hlms.aggregate(num_hlms=Count('*'), total_dwellings=Sum('num_dwellings'), avg_ivp=Round(Avg('ivp'), precision=1))
        avg_disrepair = HLMBuilding.get_disrepair_state(hlm_info['avg_ivp'])

    # Fetch any previous survey v1 entry for this building
    # If none exist, initialize a survey with the building and user ids
    # TODO: This might become slow once there are many Votes
    previous_survey_vote = Vote.objects.filter(user=request.user, eval_unit=eval_unit, surveyv1__isnull=False).first()

    if previous_survey_vote:
        log.debug('Found previous survey instance!')
        # We know the survey is not null here since we filtered on that above
        prev_survey_instance = previous_survey_vote.surveyv1
    else:
        prev_survey_instance = None

    previous_no_building_vote = Vote.objects.filter(user=request.user, eval_unit=eval_unit, nobuildingflag__isnull=False).first()

    if previous_no_building_vote:
        log.debug('Previously voted no building!')

    if request.method == "POST":
        # Save the last orientation/zoom for the building for later visits
        if 'latest_view_data' in request.POST:
            data = request.POST.getlist('latest_view_data')[0]
            if len(data) > 0: 
                data = json.loads(data)
                latest_view_data = EvalUnitLatestViewData(
                    eval_unit = eval_unit,
                    user = request.user,
                    sv_pano = data['sv_pano'],
                    sv_heading = data['sv_heading'], 
                    sv_pitch = data['sv_pitch'], 
                    sv_zoom = data['sv_zoom'], 
                    marker_lat = data['marker_lat'], 
                    marker_lng = data['marker_lng'], 
                )
                latest_view_data.save()

        if 'no_building' in request.POST:
            # Because we'll be creating multiple DB objects with relations to each other,
            # we want either all of them to be created, or none if a problem occurs.
            with transaction.atomic():
                # If the user had previously submitted a survey for the building
                # delete it and create a new no building vote instead
                if previous_survey_vote:
                    previous_survey_vote.delete()
                # Form submission - need to create a new Vote object
                # That will be references by a set of MaterialScores and an optional Note
                new_vote = Vote(eval_unit = eval_unit, user = request.user)
                new_vote.save()

                no_building = NoBuildingFlag(vote = new_vote)
                no_building.save()

            next_eval_unit_id = EvalUnit.objects.get_next_unit_to_survey(exclude_id = eval_unit.id, id_only=True)
            return redirect("buildings:survey_v1", eval_unit_id=next_eval_unit_id)

        # Handle submission of the survey
        else:
            # If previous_survey_answer is not None, we will modify the previous entry
            form = SurveyV1Form(request.POST, instance=prev_survey_instance)

            if form.is_valid():
                with transaction.atomic():
                    # Delete any previous no building vote for this building
                    # I.e. we're overwriting it.
                    if previous_no_building_vote:
                        previous_no_building_vote.delete()
                    
                    form = form.save(commit=False)
                    # If there was a previous vote by this user on this building
                    # we want to replace the previous vote and delete the previous survey
                    if previous_survey_vote:
                        # Update the modified timestamp on the vote
                        previous_survey_vote.date_modified = datetime.now()
                        previous_survey_vote.save()
                        form.vote = previous_survey_vote
                        prev_survey_instance.delete()
                    # Otherwise, we create a new vote and associate the survey to it.
                    else:
                        new_vote = Vote(eval_unit = eval_unit, user=request.user)
                        new_vote.save()
                        form.vote = new_vote
                    form.save()

                # Update the eval unit to a new one
                next_eval_unit_id = EvalUnit.objects.get_next_unit_to_survey(exclude_id = eval_unit.id, id_only = True)
                # We redirect so the URL updates to the next building ID
                return redirect("buildings:survey_v1", eval_unit_id=next_eval_unit_id)
            else:
                log.error(form.errors)

    # Fetch the latest view data for the current building if it exists
    latest_view_data_value = EvalUnitLatestViewData.objects.get_latest_view_data(eval_unit.id, request.user.id)

    if latest_view_data_value:
        latest_view_data_value = model_to_dict(latest_view_data_value, exclude=['id', 'user', 'date_added'])

    # Get the next building 
    next_eval_unit_id = EvalUnit.objects.get_next_unit_to_survey(exclude_id = eval_unit.id, id_only=True)

    form = SurveyV1Form(instance=prev_survey_instance)

    # Load the lot polygon
    # https://django.readthedocs.io/en/stable/ref/contrib/gis/functions.html
    # https://django.readthedocs.io/en/stable/ref/contrib/gis/serializers.html
    # eval_unit.geom = eval_unit.geom.simplify(0.000005)
    # lot_geojson = json.loads(serialize('geojson', [eval_unit], geometry_field='geom', fields=[]))

    from django.db import connection

    lot_geojson = None
    with connection.cursor() as cursor:
        cursor.execute(f"select st_asgeojson(st_simplify(lot_geom, 0.000005, true)) from evalunits where id = %s", [eval_unit_id])       
        row = cursor.fetchone()
        # If we get a result
        if row and row[0]:
            lot_geojson = {
                'type': 'Feature',
                'geometry': json.loads(row[0]) 
            }

    context = {
        'key': settings.GOOGLE_MAPS_API_KEY,
        'eval_unit': eval_unit,
        'eval_unit_coords': {
            'lat': eval_unit.lat,
            'lng': eval_unit.lng,
        },
        'geojson': lot_geojson,
        'latest_view_data_value': latest_view_data_value,
        'next_eval_unit_id': next_eval_unit_id,
        'form': form,
        'previous_no_building_vote': previous_no_building_vote,
        'cubf_resolved': CUBF_TO_NAME_MAP[eval_unit.cubf],
        'hlms': hlms,
        'hlm_info': hlm_info,
        'avg_disrepair': avg_disrepair,
    }
    return render(request, 'buildings/survey.html', context)


class EvalUnitDetailView(generic.DetailView):
    """
    TODO: Create a detail view for out eval units, showing votes and info summary
    """
    model = EvalUnit
    template_name = 'buildings/detail.html'



def register(request):
    if request.user.is_authenticated:
        return redirect('buildings:index')
    
    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            # This will create the user
            user = form.save()
            messages.success(request, f'Account created for {user.username}')
            return redirect('buildings:login')
    else:
        form = CreateUserForm()

    context = {'form': form}
    return render(request, 'buildings/register.html', context)


def login_page(request):
    if request.user.is_authenticated:
        return redirect('buildings:index')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            if request.GET and 'next' in request.GET:
                return redirect(request.GET['next'])
            else:
                return redirect('buildings:index')
        else:
            messages.error(request, "Username or password incorrect")
            return render(request, 'buildings/login.html')

    return render(request, 'buildings/login.html')


def logout_page(request):
    logout(request)
    return redirect('buildings:login')


@require_POST
def upload_imgs(request, eval_unit_id):
    """
    We'll process the image uploading asynchronously using a PythonAnywhere (PA) Always-on Task
    We have to do this because PA doesn't support laucnhing background threads.
    If we switch to another VPS, we should implement the background thread solution
    https://blog.pythonanywhere.com/198/
    https://www.pythonanywhere.com/forums/topic/3627/
    """
    if settings.DEBUG:
        return HttpResponse('debug mode job not created')
    data = json.loads(request.body)
    eval_unit = get_object_or_404(EvalUnit, pk=eval_unit_id)
    UploadImageJob(eval_unit=eval_unit, user=request.user, job_data=data, status=UploadImageJob.Status.PENDING).save()
    return HttpResponse('Ok')


@csrf_exempt
@require_POST
def redeploy_server(request):
    """
    Github webhook endpoint to redeploy the server on PythonAnywhere.com
    """
    if request.method != 'POST':
        return HttpResponse(status=403, reason="Invalid method")
    
    # Verify if request came from one of GitHub's IP addresses
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    client_ip_address = ip_address(forwarded_for)
    whitelist = requests.get('https://api.github.com/meta').json()['hooks']

    for valid_ip in whitelist:
        if client_ip_address in ip_network(valid_ip):
            break
    else:
        return HttpResponse(status=403, reason=f"POST to /redeploy_server came from unauthorized IP: {client_ip_address}")
    
    # Verify the secret
    secret = WEBHOOK_SECRET
    x_hub_signature = request.headers.get('x-hub-signature-256')

    if not verify_github_signature(request.body, secret, x_hub_signature):
        log.warning(f'Wrong x-hub-signature!')
        return HttpResponse(status=403, reason="x-hub-signature-256 header is missing!")
    
    # Check that this is a push event as we only want those to trigger a webhook
    # Another event would indicate misconfiguration of webhooks in GitHub
    event = request.headers.get('X-GitHub-Event')
    if event != 'push':
        return HttpResponse(status=204, reason=f"Webhook event was not 'push' but {event}")
    
    # All is good for now, get the body and check which branch was pushed
    body = json.loads(request.body)

    # We only want to redeploy when the main branch was pushed to
    ref = body['ref']
    if ref != 'refs/heads/main':
        return HttpResponse(f"Branch {ref} was pushed to. Ignore.")

    # If the main branch was pushed to, pull the newest version
    repo = git.Repo(BASE_DIR)

    # Check if there are current uncommited changes which could make the pull failed
    # If there are, we stash the changes incase they were important but do not re-apply them
    stashed = False
    if repo.is_dirty():
        log.warn(f'Repository is dirty. Stashing changes')
        repo.git.stash('save')
        stashed = True

    # If we're not on the main branch, switch to it
    if repo.active_branch != repo.refs.main:
        log.warning('Repository is not on main branch')
        repo.git.checkout('main')
    
    origin = repo.remotes.origin

    try:
        origin.pull()
    except:
        log.error(traceback.format_exc())
        return HttpResponse(status=500, reason=f'Caught an exception while pulling. See server logs for details.')
    
    if stashed:
        return HttpResponse("Updated deployed version to new main branch. Some changes were stashed!")
    
    return HttpResponse("All good!")


