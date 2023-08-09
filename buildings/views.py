import io
import git
import hmac
import json
import hashlib
import requests
import traceback

from PIL import Image
from pprint import pprint
from w3lib.url import parse_data_uri
from uuid_extensions import uuid7str
from ipaddress import ip_address, ip_network

from django.views import generic 
from django.conf import settings
from django.db import transaction
from django.contrib import messages 
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.forms.models import model_to_dict
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404, render, redirect

from .utils import b2_upload
from .forms import CreateUserForm
from .models.surveys import SurveyV1Form
from config.settings import B2_APPKEY_RW, B2_BUCKET_IMAGES, B2_ENDPOINT, B2_KEYID_RW, WEBHOOK_SECRET, BASE_DIR
from .models.models import EvalUnit, EvalUnitSatelliteImage, EvalUnitStreetViewImage, EvalUnitLatestViewData, NoBuildingFlag, Vote
import logging

log = logging.getLogger(__name__)

@login_required(login_url='buildings:login')
def index(request):

    random_building = EvalUnit.objects.get_random_unvoted()

    latest_votes = Vote.objects.get_latest(n=5)

    # If all buildings have votes, return a random building from the least voted ones
    if random_building is None:
        random_building = EvalUnit.objects.get_random_least_voted()

    context = {
        "random_unscored_building_id": random_building.id,
        "latest_votes": latest_votes
    }
    return render(request, 'buildings/index.html', context)


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
def survey(request):
    random_unscored_unit = EvalUnit.objects.get_next_unit_to_survey()
    eval_unit_id = random_unscored_unit.id
    return redirect('buildings:survey_v1', eval_unit_id=eval_unit_id)


@login_required(login_url='buildings:login')
def survey_v1(request, eval_unit_id):

    eval_unit = get_object_or_404(EvalUnit, pk=eval_unit_id)

    # Fetch any previous survey v1 entry for this building
    # If none exist, initialize a survey with the building and user ids
    previous_survey_vote = Vote.objects.filter(user=request.user, eval_unit=eval_unit, surveyv1__isnull=False).first()
    previous_no_building_vote = Vote.objects.filter(user=request.user, eval_unit=eval_unit, nobuildingflag__isnull=False).first()

    if previous_survey_vote:
        log.debug('Found previous survey instance!')
        prev_survey_instance = previous_survey_vote.surveyv1
    else:
        prev_survey_instance = None

    if previous_no_building_vote:
        log.debug('Previously voted no building!')

    # TODO: Do we still need the no building flag? 
    if request.method == "POST":
        log.debug('request.POST:')   
        log.debug(pprint(request.POST))

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

            next_eval_unit = EvalUnit.objects.get_next_unit_to_survey(exclude_id = eval_unit.id)
            return redirect("buildings:survey_v1", eval_unit_id=next_eval_unit.id)

        # Handle submission of survey version 1
        elif 'survey_version' in request.POST and request.POST.get('survey_version') == '1.0':
            # If previous_survey_answer is not None, we will modify the previous entry
            form = SurveyV1Form(request.POST, instance=prev_survey_instance)

            if form.is_valid():
                log.debug('cleaned_data:')
                log.debug(pprint(form.cleaned_data))

                with transaction.atomic():
                    # Delete any previous no building vote for this building
                    # I.e. we're overwriting it.
                    if previous_no_building_vote:
                        previous_no_building_vote.delete()
                    new_vote = Vote(eval_unit = eval_unit, user=request.user)
                    new_vote.save()

                    form = form.save(commit=False)
                    form.vote = new_vote
                    form.save()

                # Update the eval unit to a new one
                next_eval_unit = EvalUnit.objects.get_next_unit_to_survey(exclude_id = eval_unit.id)
                # We redirect so the URL updates to the next building ID
                return redirect("buildings:survey_v1", eval_unit_id=next_eval_unit.id)
            else:
                log.error(form.errors)

    # Fetch the latest view data for the current building if it exists
    latest_view_data = EvalUnitLatestViewData.objects.get_latest_view_data(eval_unit.id, request.user.id)

    if latest_view_data:
        latest_view_data = model_to_dict(latest_view_data, exclude=['id', 'user', 'date_added'])

    # Get the next building 
    next_eval_unit = EvalUnit.objects.get_next_unit_to_survey(exclude_id = eval_unit.id)

    form = SurveyV1Form(instance=prev_survey_instance)

    context = {
        # TODO: Is this the best way to pass API keys to views?
        'key': settings.GOOGLE_MAPS_API_KEY,
        'eval_unit': eval_unit,
        'latest_view_data': latest_view_data,
        'next_eval_unit': next_eval_unit.id,
        'form': form,
        'previous_no_building_vote': previous_no_building_vote
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
            return redirect('buildings:index')
        else:
            messages.error(request, "Username or password incorrect")
            return render(request, 'buildings/login.html')

    return render(request, 'buildings/login.html')


def logout_page(request):
    logout(request)
    return redirect('buildings:login')


@require_POST
def upload_imgs(request, building_id):
    # Receive the images from the frontend
    body = json.loads(request.body)

    b2 = b2_upload.get_b2_resource(B2_ENDPOINT, B2_KEYID_RW, B2_APPKEY_RW)

    building = get_object_or_404(EvalUnit, pk=building_id)

    # Add any kind of metadata to be associated with the image
    extra_args = {
        'Metadata': {
            'user': request.user.username,
        }
    }

    upload_formats_and_sizes = [('large', 2400), ('medium', 1200), ('small', 400)]

    for image_type in body.keys():
        print(image_type)

        if data_uri := body.get(image_type):
            data = parse_data_uri(data_uri)
            image = Image.open(io.BytesIO(data.data))
            # Convert the image to RGB to save as JPG
            image = image.convert('RGB')

        if not image:
            return HttpResponse("Fail")
        
        # For streetview images, we'll store multiple sizes 
        if image_type == 'streetview':
            # Streetview pics of all sizes will share a UUID
            uuid = uuid7str()
            # We'll do an all or nothing save here. 
            # If an exception occurs during saving any of the sizes
            # we won't save the link in the DB. On the other hand, if 
            # we have a link in the DB, we know that all sizes exist.
            # This could result in stranded images in B2 if only some uploads fail.
            try:
                for format, size in upload_formats_and_sizes: 
                    # Resize the image, maintaining the aspect ratio
                    image.thumbnail((size, size))
                    print(image.size)
                    # Create an in memory file to temporarily store the image
                    in_mem_file = io.BytesIO()
                    image.save(in_mem_file, format='jpeg')
                    in_mem_file.seek(0)

                    # Try to upload the image
                    b2.Bucket(B2_BUCKET_IMAGES).upload_fileobj(
                        in_mem_file,
                        f"images/streetview/{format}/{uuid}.jpg",
                        ExtraArgs=extra_args
                    )

                # Only need to save the UUID in DB once, since formats share it
                EvalUnitStreetViewImage(building=building, uuid=uuid, user=request.user).save()
            except:
                print(traceback.format_exc())
            
            in_mem_file.close()

        elif image_type == 'satellite':
            uuid = uuid7str()
            # Resize the image, maintaining the aspect ratio
            image.thumbnail((1200, 1200))
            # Create an in memory file to temporarily store the image
            in_mem_file = io.BytesIO()
            # Convert to JPEG for space, it's about 4 times smaller
            image.save(in_mem_file, format='jpeg')
            in_mem_file.seek(0)
            try:
                # Try to upload the image
                b2.Bucket(B2_BUCKET_IMAGES).upload_fileobj(
                    in_mem_file,
                    f"images/satellite/medium/{uuid}.jpg",
                    ExtraArgs=extra_args
                )
                EvalUnitSatelliteImage(building=building, uuid=uuid, user=request.user).save()
            except:
                print(traceback.format_exc())
            in_mem_file.close()

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

    if not verify_signature(request.body, secret, x_hub_signature):
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


def verify_signature(payload_body, secret_token, signature_header):
    """Verify that the payload was sent from GitHub by validating SHA256.
    
    Args:
        payload_body: original request body to verify (request.body())
        secret_token: GitHub app webhook token (WEBHOOK_SECRET)
        signature_header: header received from GitHub (x-hub-signature-256)
    """
    if not signature_header:
        return False
    
    hash_object = hmac.new(secret_token.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()

    if not hmac.compare_digest(expected_signature, signature_header):
        return False
    
    return True
