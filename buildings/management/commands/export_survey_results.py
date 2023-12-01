import json
import IPython
import logging
import botocore
import traceback
from pathlib import Path
from itertools import chain
from buildings.utils.b2_upload import get_client

from buildings.models.models import EvalUnitSatelliteImage, EvalUnitStreetViewImage

from django.core.management.base import BaseCommand

from config.settings import B2_BUCKET_IMAGES, BASE_DIR
DEFAULT_OUT = BASE_DIR / 'output' / 'img_dataset'

log = logging.getLogger(__name__)

B2_CLIENT = get_client()


class Command(BaseCommand):
    help = "Download the screenshot and survey dataset."

    def add_arguments(self, parser):
        parser.add_argument("--download-images", action="store_true", default=False)
        parser.add_argument("--output-dir", nargs='?', default=DEFAULT_OUT, type=Path)

    def handle(self, *args, **options):

        output_dir: Path = options['output_dir']
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Create all directories for images
        if options['download_images']: 
            sv_images_dir = output_dir / 'sv'
            sat_images_dir = output_dir / 'sat'
            for sz in ['s', 'm', 'l']:
                Path(sv_images_dir / sz).mkdir(exist_ok=True, parents=True)
                Path(sat_images_dir / sz).mkdir(exist_ok=True, parents=True)


        sv_dataset = {}
        sat_dataset = {}

        # Create a generator with all images
        all_images = chain(EvalUnitStreetViewImage.objects.iterator(), EvalUnitSatelliteImage.objects.iterator())
        
        for img in all_images:

            img_type = 'streetview' if isinstance(img, EvalUnitStreetViewImage) else 'satellite'

            eval_unit = img.eval_unit
            survey_votes = eval_unit.vote_set.filter(surveyv1__isnull = False)

            if (len(survey_votes) > 1):
                raise Exception(f'Eval unit {eval_unit.id} has more than 1 survey answer. Need to find a way to reduce the multiple survey answers to a single one!')
            
            if len(survey_votes) == 0:
                log.warning(f'No vote associated with img {img.uuid} on unit {img.eval_unit}')
                continue
            
            if options['download_images']:
                img_dir = sv_images_dir if isinstance(img, EvalUnitStreetViewImage) else sat_images_dir

                for sz in ['s', 'm', 'l']:
                    file_name = f'{img_dir}/{sz}/{img.uuid}.jpg'
                    key = f'screenshots/{img_type}/{sz}/{img.uuid}.jpg'

                    try:
                        with open(file_name, 'wb') as outfile:
                            B2_CLIENT.download_fileobj(B2_BUCKET_IMAGES, key, outfile)
                    except botocore.exceptions.ClientError as e:
                        log.error(e)
                    except:
                        log.error(traceback.format_exc())
                        log.error(f'Could not download {key}')
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

            if img_type == 'streetview':
                # Add the iamge data to the dataset
                sv_dataset[img.uuid] = img_data
            else:
                sat_dataset[img.uuid] = img_data


        with open(output_dir / 'sv.json', 'w', encoding='utf-8') as sv_out:
            json.dump(sv_dataset, sv_out, ensure_ascii=False, indent=2)

        with open(output_dir/ 'sat.json', 'w', encoding='utf-8') as sat_out:
            json.dump(sat_dataset, sat_out, ensure_ascii=False, indent=2)

            

        