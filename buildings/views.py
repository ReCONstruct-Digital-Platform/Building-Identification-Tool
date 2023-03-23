from django.views import generic 
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.contrib import messages 
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import get_object_or_404, render, redirect

from .models import Building, Material, Vote, BuildingNote, MaterialScore, Profile
from .forms import CreateUserForm
from django.core.paginator import Paginator

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
        # Create a new DB transaction which will make the following code
        # either all happen and be committed to the database, or fully rolled back.
        # This is called atomicity.
        #
        # Because we'll be creating multiple DB objects with relations to each other,
        # we want either all of them to be created, or none if a problem occurs.
        with transaction.atomic():
            # Form submission - need to create a new Vote object
            # That will be references by a set of MaterialScores and an optional Note
            new_vote = Vote(building = building, user = request.user)
            new_vote.save()

            logging.debug(request.POST)

            for key in request.POST:
                if "material" in key:
                    # Expect the value to be an array with 2 values, material name and 1-5 score
                    value = request.POST.getlist(key)
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

                elif "note" in key:
                    value = request.POST.getlist(key)
                    note = BuildingNote(vote=new_vote, note=value[0])
                    note.save()

                elif "typology" in key:
                    # Expect the value to be an array with 2 values, typology name and 1-5 score
                    value = request.POST.getlist(key)
                    typology_name = value[0]
                    score = value[1]
                    pass

            # Finally, we can save our vote
            new_vote.save()
            # Get the new current building
            building = Building.objects.get_next_building_to_classify(exclude_id = building.id)

    # Get the next building
    next_building_id = Building.objects.get_next_building_to_classify(exclude_id = building.id)
    # Get all unique materials defined 
    existing_materials = [o['name'].capitalize() for o in Material.objects.all().values('name').distinct()]

    context = {
        # TODO: Is this the best way to pass API keys to views?
        'key': settings.GOOGLE_API_KEY,
        'building': building,
        'existing_materials': existing_materials,
        'next_building': next_building_id.id,
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
