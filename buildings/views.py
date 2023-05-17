import os
import hmac
import json
import hashlib

from django.views import generic 
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.contrib import messages 
from django.http import HttpResponse
from django.forms.models import model_to_dict
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404, render, redirect


from .forms import CreateUserForm
from django.core.paginator import Paginator
from .models import Building, BuildingLatestViewData, BuildingTypology, Material, NoBuildingFlag, Typology, Vote, BuildingNote, MaterialScore, Profile

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

    if request.method == "POST":
        # Because we'll be creating multiple DB objects with relations to each other,
        # we want either all of them to be created, or none if a problem occurs.
        with transaction.atomic():
            # Form submission - need to create a new Vote object
            # That will be references by a set of MaterialScores and an optional Note
            new_vote = Vote(building = building, user = request.user)
            new_vote.save()

            logging.debug(request.POST)

            for key in request.POST:
                if "typology" in key:
                    # Expect the value to be an array with 2 values, typology name and 1-5 score
                    value = request.POST.getlist(key)
                    if len(value) > 1:
                        typology_name = value[0]
                        score = value[1]

                        typology = Typology.objects.filter(name__icontains=typology_name).first()
                        if typology is None:
                            typology = Typology(name=typology_name)
                            typology.save()
                        
                        # Create a new MaterialScore linking this vote, the material and the score
                        building_typology = BuildingTypology(vote=new_vote, typology=typology, score=score)
                        building_typology.save()

                elif "note" in key:
                    value = request.POST.getlist(key)[0]
                    # If the note value is not empty, save a note for the building
                    if value != '':
                        note = BuildingNote(vote=new_vote, note=value)
                        note.save()

                elif "material" in key:
                    # Expect the value to be an array with 2 values, material name and 1-5 score
                    value = request.POST.getlist(key)
                    if len(value) > 1:
                        material_name = value[0]
                        score = value[1]
                        # Get a reference to the material
                        material = Material.objects.filter(name__icontains=material_name).first()

                        logging.debug(f"Found material {material}")
                        # If it doesn't exist, create a new material
                        if material is None:
                            material = Material(name=material_name)
                            material.save()
                        
                        # Create a new MaterialScore linking this vote, the material and the score
                        material_score = MaterialScore(vote=new_vote, material=material, score=score)
                        material_score.save()

                elif key == "latest_view_data":

                    data = request.POST.getlist(key)[0]
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

                elif key == 'no_building':
                    no_building = NoBuildingFlag(vote = new_vote)
                    no_building.save()

            # Finally, we can save our vote
            new_vote.save()
            # Get the new current building
            building = Building.objects.get_next_building_to_classify(exclude_id = building.id)

        next_building = Building.objects.get_next_building_to_classify(exclude_id = building.id)

        return redirect("buildings:classify", building_id=next_building.id)
    
    building_latest_view_data = BuildingLatestViewData.objects.get_latest_view_data(building.id, request.user.id)

    if building_latest_view_data:
        building_latest_view_data = model_to_dict(building_latest_view_data, exclude=['id', 'user', 'date_added'])

    # Get the next building 
    next_building = Building.objects.get_next_building_to_classify(exclude_id = building.id)

    context = {
        # TODO: Is this the best way to pass API keys to views?
        'key': settings.GOOGLE_MAPS_API_KEY,
        'building': building,
        'building_latest_view_data': building_latest_view_data,
        'next_building': next_building.id,
    }
    return render(request, 'buildings/map.html', context)


class DetailView(generic.DetailView):
    model = Building
    template_name = 'buildings/detail.html'

    def get_queryset(self):
        """
        Excludes any questions that aren't published yet.
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


@csrf_exempt
def redeploy_server(request):
    """
    Github webhook endpoint to redeploy the server on PythonAnywhere.com
    """
    if request.method != 'POST':
        return HttpResponse(status=403, reason="Invalid method")
    # signature is OK
    # print(request.body)
    body = json.loads(request.body)
    log.info(f'body received: {body}')

    x_hub_signature = request.headers.get('x-hub-signature-256')
    print(x_hub_signature)

    secret = os.environ['WEBHOOK_SECRET']
    print(secret)

    if not verify_signature(request.body, secret, x_hub_signature):
        log.warning(f'Wrong x-hub-signature!')
        return HttpResponse(status=403, reason="x-hub-signature-256 header is missing!")
    

    return HttpResponse("OK")


def verify_signature(payload_body, secret_token, signature_header):
    """Verify that the payload was sent from GitHub by validating SHA256.
    
    Raise and return 403 if not authorized.
    
    Args:
        payload_body: original request body to verify (request.body())
        secret_token: GitHub app webhook token (WEBHOOK_SECRET)
        signature_header: header received from GitHub (x-hub-signature-256)
    """
    if not signature_header:
        return HttpResponse(status=403, reason="x-hub-signature-256 header is missing!")
    
    hash_object = hmac.new(secret_token.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()

    if not hmac.compare_digest(expected_signature, signature_header):
        return HttpResponse(status=403, reason="Request signatures didn't match!")
