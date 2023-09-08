import json
import os
import environ
from pathlib import Path
import csv
import logging
import traceback
import IPython
from itertools import chain

import psycopg2
import psycopg2.extras
from time import sleep
from pprint import pprint
from functools import reduce
from django.conf import settings
from uuid_extensions import uuid7str
from buildings.models.models import EvalUnit, EvalUnitSatelliteImage, EvalUnitStreetViewImage, UploadImageJob, User

from django.core.management.base import BaseCommand

from config.settings import BASE_DIR
DEFAULT_OUT = BASE_DIR / 'output'

log = logging.getLogger(__name__)



class Command(BaseCommand):
    help = "Download the screenshot and survey dataset."

    def add_arguments(self, parser):
        parser.add_argument("output_dir", nargs='?', default=DEFAULT_OUT, type=Path)

    def handle(self, *args, **options):

        output_dir: Path = options['output_dir']
        output_dir.mkdir(exist_ok=True, parents=True)

        sv_dataset = {}
        sat_dataset = {}

        # Create a generator with all images
        all_images = chain(EvalUnitStreetViewImage.objects.iterator(), EvalUnitSatelliteImage.objects.iterator())
        
        for img in all_images:

            eval_unit = img.eval_unit
            survey_votes = eval_unit.vote_set.filter(surveyv1__isnull = False)

            if (len(survey_votes) > 1):
                raise Exception(f'Eval unit {eval_unit.id} has more than 1 survey answer. Need to find a way to reduce the multiple survey answers to a single one!')
            
            if len(survey_votes) == 0:
                log.warning(f'No vote associated with img {img.uuid} on unit {img.eval_unit}')
                continue
            
            survey = survey_votes.first().surveyv1

            img_data = {
                'eval_unit_id': eval_unit.id,
                'user': img.user.username
            }

            for field, value in survey.__dict__.items():
                if field in ['_state', 'id', 'vote_id']:
                    continue
                # add the survey answer to the img data
                img_data[field] = value

            if isinstance(img, EvalUnitStreetViewImage):
                # Add the iamge data to the dataset
                sv_dataset[img.uuid] = img_data
            else:
                sat_dataset[img.uuid] = img_data


        with open(output_dir / 'sv.json', 'w', encoding='utf-8') as sv_out:
            json.dump(sv_dataset, sv_out, ensure_ascii=False, indent=2)

        with open(output_dir/ 'sat.json', 'w', encoding='utf-8') as sat_out:
            json.dump(sat_dataset, sat_out, ensure_ascii=False, indent=2)

            

        