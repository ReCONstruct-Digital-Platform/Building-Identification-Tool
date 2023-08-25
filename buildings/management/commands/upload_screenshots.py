import io
import json
import logging
import traceback
from PIL import Image
from time import sleep
from pprint import pprint
from functools import reduce
from w3lib.url import parse_data_uri
from uuid_extensions import uuid7str
from buildings.utils import b2_upload
from buildings.models.models import EvalUnit, EvalUnitSatelliteImage, EvalUnitStreetViewImage, UploadImageJob, User


from django.core.management.base import BaseCommand

log = logging.getLogger(__name__)

# Modify or add new image sizes here
IMAGE_SIZES = [('l', 1200), ('m', 700), ('s', 300)]


def get_pending_jobs():
    return UploadImageJob.objects.filter(status=UploadImageJob.Status.PENDING).order_by('date_added')


def process_job(job: UploadImageJob):
    # Label the job as in progress
    job.status = UploadImageJob.Status.IN_PROGRESS
    job.save()

    # Metadata associated with the images
    # Upload date is already available from B2
    extra_args = {
        'Metadata': {
            'user': job.user.username,
            'eval_unit': job.eval_unit.id,  # add a reverse link to eval unit
        }
    }

    # create 2 UUIDs to be shared by images of the same type
    # We consider streetview and satellite images separately bc
    # there will usually be more streetview images than sartellite
    # due to there being multiple interesting angles of a building facade
    UUIDs = {
        'streetview': uuid7str(),
        'satellite': uuid7str()
    }
    in_mem_file = None

    try:
        for image_type in ['streetview', 'satellite']:
            if data_uri := job.job_data[image_type]:
                data = parse_data_uri(data_uri)
                image = Image.open(io.BytesIO(data.data))
                # Convert the image to RGB to save as JPG
                image = image.convert('RGB')

            uuid = UUIDs[image_type]
            log.debug(f'Screenshot {uuid}: Original {image_type} image size: {image.size}')

            # We'll do an all or nothing save here. 
            # If an exception occurs during saving any of the sizes
            # we won't save the link in the DB. On the other hand, if 
            # we have a link in the DB, we know that all sizes exist.
            # This could result in stranded images in B2 if only some uploads fail.
            for format, size in IMAGE_SIZES: 
                # Resize the image, maintaining the aspect ratio
                image.thumbnail((size, size))
                # Create an in memory file to temporarily store the image
                in_mem_file = io.BytesIO()
                image.save(in_mem_file, format='jpeg')
                in_mem_file.seek(0)

                log.debug(f'Screenshot {uuid}: uploading {image_type} format {format} of size {image.size}')
                # Try to upload the image
                b2_upload.upload_image(
                    in_mem_file,
                    f"screenshots/{image_type}/{format}/{uuid}.jpg",
                    extra_args
                )

            # Only need to save the UUID in DB once, since diff sizes share it
            if image_type == 'streetview':
                EvalUnitStreetViewImage(eval_unit=job.eval_unit, uuid=uuid, user=job.user).save()
            elif image_type == 'satellite':
                EvalUnitSatelliteImage(eval_unit=job.eval_unit, uuid=uuid, user=job.user).save()
            

        log.info(f'Screenshot {uuid}: successfully uploaded!')
        # Can't delete the job here - I get
        # ValueError: UploadImageJob object can't be deleted because its id attribute is set to None.
        job.status = UploadImageJob.Status.DONE
        # Delete the (large) image data from successful jobs
        job.job_data = {}
        job.save()
        return 0
    except:
        log.error(traceback.format_exc())
        job.status = UploadImageJob.Status.ERROR
        job.save()
    finally:
        if in_mem_file:
            in_mem_file.close()
        return 1


class Command(BaseCommand):
    help = "Check for pending image upload jobs in the DB and process them"

    def handle(self, *args, **options):
        
        sleep_time = 1
        num_checks = 0
        log.info(f"Checking for pending jobs every {sleep_time}s")

        while True:
            if jobs := get_pending_jobs():
                log.info(f"Starting processing on {len(jobs)} job{'s' if len(jobs) > 1 else ''}")

                # Process all jobs, deleting successful ones
                for job in jobs:
                    process_job(job)

                # TODO: Periodic cleanup of images, probably use a scheduled task for this
                # for job in jobs:
                #     if job.status == UploadImageJob.Status.DONE:
                #         job.delete()

                # If pending job found, reset the retry policy to checks every 1s
                sleep_time = 1
                num_checks = 0
            else:
                sleep(sleep_time)
                num_checks += 1

                # Check for pending jobs every second for 10 minutes
                # If nothing after 10min, start checking every 5 seconds
                # If nothing after 1h, start checking every 10 seconds
                # If pending job found, revert to old regime
                if sleep_time == 1 and num_checks == 600:
                    sleep_time = 5
                    num_checks = 0
                    log.info(f'No pending jobs found in last 10 minutes. Switching to {sleep_time}s sleep time')
                elif sleep_time == 5 and num_checks == 720:
                    sleep_time = 10
                    num_checks = 0
                    log.info(f'No pending jobs found in last hour. Switching to {sleep_time}s sleep time')
