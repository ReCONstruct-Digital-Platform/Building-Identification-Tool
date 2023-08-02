import io
import git
import hmac
import json
import boto3
import hashlib
import requests
import traceback

from PIL import Image
from w3lib.url import parse_data_uri
from uuid_extensions import uuid7str
from ipaddress import ip_address, ip_network

from django.views import generic 
from django.conf import settings
from django.db import transaction
from django.utils import timezone
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
from .models.models import Building, BuildingSatelliteImage, BuildingStreetViewImage, BuildingLatestViewData, BuildingTypology, Material, NoBuildingFlag, Typology, Vote, BuildingNote, MaterialScore, Profile

import logging

log = logging.getLogger(__name__)

@login_required(login_url='buildings:login')
def index(request):

    random_building = Building.objects.get_random_unvoted()

    latest_votes = Vote.objects.get_latest(n=5)

    # If all buildings have votes, return a random building from the least voted ones
    if random_building is None:
        random_building = Building.objects.get_random_least_voted()

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

    ordering, direction = Building.get_ordering(order_by, dir)
    log.debug(f'Ordering: {ordering}, direction: {direction}')
    qs = Building.objects.search(query=query, ordering=ordering)

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
def classify_home(request):
    random_unscored_building = Building.objects.get_next_building_to_classify()
    building_id = random_unscored_building.id
    return redirect('buildings:classify', building_id=building_id)


@login_required(login_url='buildings:login')
def classify(request, building_id):

    building = get_object_or_404(Building, pk=building_id)

    # Could check if a previous vote already exists for the building
    # and return the filled form if it's the case!

    if request.method == "POST":
        # # Because we'll be creating multiple DB objects with relations to each other,
        # # we want either all of them to be created, or none if a problem occurs.
        # with transaction.atomic():
        #     # Form submission - need to create a new Vote object
        #     # That will be references by a set of MaterialScores and an optional Note
        #     new_vote = Vote(building = building, user = request.user)
        #     new_vote.save()

        #     log.debug(request.POST)

        #     for key in request.POST:
        #         if "typology" in key:
        #             # Expect the value to be an array with 2 values, typology name and 1-5 score
        #             value = request.POST.getlist(key)
        #             if len(value) > 1:
        #                 typology_name = value[0]
        #                 score = value[1]

        #                 typology = Typology.objects.filter(name__icontains=typology_name).first()
        #                 if typology is None:
        #                     typology = Typology(name=typology_name)
        #                     typology.save()
                        
        #                 # Create a new MaterialScore linking this vote, the material and the score
        #                 building_typology = BuildingTypology(vote=new_vote, typology=typology, score=score)
        #                 building_typology.save()

        #         elif "note" in key:
        #             value = request.POST.getlist(key)[0]
        #             # If the note value is not empty, save a note for the building
        #             if value != '':
        #                 note = BuildingNote(vote=new_vote, note=value)
        #                 note.save()

        #         elif "material" in key:
        #             # Expect the value to be an array with 2 values, material name and 1-5 score
        #             value = request.POST.getlist(key)
        #             if len(value) > 1:
        #                 material_name = value[0]
        #                 score = value[1]
        #                 # Get a reference to the material
        #                 material = Material.objects.filter(name__icontains=material_name).first()

        #                 log.debug(f"Found material {material}")
        #                 # If it doesn't exist, create a new material
        #                 if material is None:
        #                     material = Material(name=material_name)
        #                     material.save()
                        
        #                 # Create a new MaterialScore linking this vote, the material and the score
        #                 material_score = MaterialScore(vote=new_vote, material=material, score=score)
        #                 material_score.save()

        #         elif key == "latest_view_data":

        #             data = request.POST.getlist(key)[0]
        #             if len(data) > 0: 
        #                 data = json.loads(data)

        #                 latest_view_data = BuildingLatestViewData(
        #                     building = building,
        #                     user = request.user,
        #                     sv_pano = data['sv_pano'],
        #                     sv_heading = data['sv_heading'], 
        #                     sv_pitch = data['sv_pitch'], 
        #                     sv_zoom = data['sv_zoom'], 
        #                     marker_lat = data['marker_lat'], 
        #                     marker_lng = data['marker_lng'], 
        #                 )
        #                 latest_view_data.save()

        #         elif key == 'no_building':
        #             NoBuildingFlag(vote = new_vote).save()

        #     # Finally, we can save our vote
        #     new_vote.save()
        #     # Get the new current building
        #     building = Building.objects.get_next_building_to_classify(exclude_id = building.id)
        
        if 'latest_view_data' in request.POST:
            data = request.POST.getlist('latest_view_data')[0]
            if len(data) > 0: 
                data = json.loads(data)

                latest_view_data = BuildingLatestViewData(
                    building = building,
                    user = request.user,
                    sv_pano = data['sv_pano'],
                    sv_heading = data['sv_heading'], 
                    sv_pitch = data['sv_pitch'], 
                    sv_zoom = data['sv_zoom'], 
                    marker_lat = data['marker_lat'], 
                    marker_lng = data['marker_lng'], 
                )
                latest_view_data.save()

        if 'survey_version' in request.POST and request.POST.get('survey_version') == '1.0':
            form = SurveyV1Form(request.POST)
            from pprint import pprint
            pprint(request.POST)

            if form.is_valid():
                pprint(form.cleaned_data)
                next_building = Building.objects.get_next_building_to_classify(exclude_id = building.id)
                return redirect("buildings:classify", building_id=next_building.id)
            else:
                print(form.errors)
        
    building_latest_view_data = BuildingLatestViewData.objects.get_latest_view_data(building.id, request.user.id)

    if building_latest_view_data:
        building_latest_view_data = model_to_dict(building_latest_view_data, exclude=['id', 'user', 'date_added'])

    # Get the next building 
    next_building = Building.objects.get_next_building_to_classify(exclude_id = building.id)

    form = SurveyV1Form()

    context = {
        # TODO: Is this the best way to pass API keys to views?
        'key': settings.GOOGLE_MAPS_API_KEY,
        'building': building,
        'building_latest_view_data': building_latest_view_data,
        'next_building': next_building.id,
        'form': form
    }
    return render(request, 'buildings/map.html', context)


class DetailView(generic.DetailView):
    model = Building
    template_name = 'buildings/detail.html'

    def get_queryset(self):
        """
        Excludes any questions that aren't published yet.
        TODO: This is from the tutorial, remove and create a detail view
        """
        return Building.objects.filter(pub_date__lte=timezone.now())


def register(request):
    if request.user.is_authenticated:
        return redirect('buildings:index')
    
    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            # This will create the user
            user = form.save()
            Profile(user=user).save()
            messages.success(request, f'Account created for {form.cleaned_data.get("username")}')

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

    building = get_object_or_404(Building, pk=building_id)

    # Add any kind of metadata to be associated with the image
    extra_args = {
        'Metadata': {
            'user': request.user.username,
        }
    }

    upload_formats_and_sizes = [('large', 2400), ('medium', 1200), ('small', 400)]

    for image_type in body.keys():
        print(image_type)
        data = parse_data_uri(body.get(image_type))
        image = Image.open(io.BytesIO(data.data))
        # Convert the image to RGB to save as JPG
        image = image.convert('RGB')
        
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
                BuildingStreetViewImage(building=building, uuid=uuid, user=request.user).save()
            except:
                print(traceback.format_exc())
            
            in_mem_file.close()

        elif image_type == 'satellite':
            uuid = uuid7str()
            # Resize the image, maintaining the aspect ratio
            image.thumbnail((1200, 1200))
            # Create an in memory file to temporarily store the image
            in_mem_file = io.BytesIO()
            image.save(in_mem_file, format='jpeg')
            in_mem_file.seek(0)
            try:
                # Try to upload the image
                b2.Bucket(B2_BUCKET_IMAGES).upload_fileobj(
                    in_mem_file,
                    f"images/satellite/medium/{uuid}.jpg",
                    ExtraArgs=extra_args
                )
                BuildingSatelliteImage(building=building, uuid=uuid, user=request.user).save()
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
