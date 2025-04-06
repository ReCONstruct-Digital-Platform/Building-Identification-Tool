"""
This management command is intended to run as an always-on task on pythonanywhere.com
It loops forever, checking for pending image upload jobs and processing them.
"""
import io
import json
import logging
import traceback
from PIL import Image
from time import sleep
from pprint import pprint
from functools import reduce
from datetime import datetime
from w3lib.url import parse_data_uri
from uuid_extensions import uuid7str
from buildings.utils import b2
from django.core.management.base import BaseCommand
from buildings.models.models import UploadImageJob
from buildings.models.newmodels import Building
from config.settings import B2_BUCKET_IMAGES

log = logging.getLogger(__name__)

# Modify or add new image sizes here
IMAGE_SIZES = [("l", None), ("m", 750), ("s", 325)]

# Each job can have multiple MB image data
MAX_JOBS_LOADED = 10

def get_pending_jobs():
    return UploadImageJob.objects.filter(status=UploadImageJob.Status.PENDING).order_by('date_added')[:MAX_JOBS_LOADED]


def process_job(job: UploadImageJob):

    b2_client = b2.get_client()

    building: Building = job.building
    user = job.user
    job_data = job.job_data
    job_metadata = job.job_metadata

    image_type = job_data["image_type"]
    image = job_data["image"]
    uuid = job_data["uuid"]

    dataset = building.dataset

    upload_metadata = {
        "user": user.username,
        "user_id": user.id,
        "building_id": building.id,
        "building_slug": building.slug,
        "upload_date": datetime.now().isoformat(),
        **job_metadata,
    }

    # Metadat must be all string
    # Gets done automatically when using the bucket resource, but not when using the client
    for k, v in upload_metadata.items():
        upload_metadata[k] = str(v)

    in_mem_file = None

    try:
        lat = job_metadata["lat"]
        lng = job_metadata["lng"]

        if image_type == "sv":

            pano_date = job_metadata["pano_date"]
            sv_pano = job_metadata["sv_pano"]
            sv_heading = job_metadata["sv_heading"]
            sv_pitch = job_metadata["sv_pitch"]
            sv_zoom = job_metadata["sv_zoom"]
            filename = f"sv_{uuid}_{lat}_{lng}_{pano_date}_{sv_pano}_{sv_heading}_{sv_pitch}_{sv_zoom}.jpg"

        elif image_type == "sat":
            zoom = job_metadata["zoom"]
            tilt = job_metadata["tilt"]
            map_type = job_metadata["map_type"]
            filename = f"sat_{uuid}_{lat}_{lng}_{zoom}_{tilt}_{map_type}.jpg"

        else:
            raise Exception(
                f"Unknown image type {image_type}: {job_data} {job_metadata}"
            )

        data = parse_data_uri(image)
        image: Image = Image.open(io.BytesIO(data.data))
        # Convert the image to RGB to save as JPG
        image = image.convert("RGB")

        log.debug(f"Screenshot {building.slug} image size: {image.size}")

        # We'll do an all or nothing save here.
        # If an exception occurs during saving any of the sizes
        # we won't save the link in the DB. On the other hand, if
        # we have a link in the DB, we know that all sizes exist.
        # This could result in stranded images in B2 if only some uploads fail.
        for image_size, image_width in IMAGE_SIZES:

            if image_size != "l":
                # Resize the image, maintaining the aspect ratio
                image.thumbnail((image_width, image_width))

            # Create an in memory file to temporarily store the image
            in_mem_file = io.BytesIO()
            image.save(in_mem_file, format="jpeg")
            in_mem_file.seek(0)

            # TODO: Add tenant handling here
            key = f"reconstruct/{dataset.slug}/{building.slug}/{image_size}/{filename}"

            # Try to upload the image
            b2_client.upload_fileobj(
                Fileobj=in_mem_file,
                Bucket=B2_BUCKET_IMAGES,
                Key=key,
                ExtraArgs={"Metadata": upload_metadata},
            )
            log.info(f"Uploaded {key}")

            # If the building does not have a thumbnail yet, copy a small file to the thumbnail dir
            if not building.has_thumbnail and image_size == "s":
                # TODO: Add tenant handling here
                dest_key = f"reconstruct/{dataset.slug}/{building.slug}/thumbnail.jpg"
                # Copy operation source needs bucket name prepended to the key
                source_key = f"{B2_BUCKET_IMAGES}/{key}"

                # Copy the first file to thumbnail dir
                b2_client.copy_object(
                    Bucket=B2_BUCKET_IMAGES,
                    CopySource=source_key,
                    Key=dest_key,
                )
                building.has_thumbnail = True
                building.save()
                log.info(f"Thumbnail created: {dest_key}")

        log.info(f"Screenshots for {building.slug} uploaded successfully")

        # Can't delete the job here - I get
        # ValueError: UploadImageJob object can't be deleted because its id attribute is set to None.
        job.status = UploadImageJob.Status.DONE
        # Delete the (large) image data from successful jobs
        job.job_data = {}
        job.save()
        return 0
    except Exception as e:
        log.error(traceback.format_exc())
        job.status = UploadImageJob.Status.ERROR
        job.save()
    finally:
        if in_mem_file:
            in_mem_file.close()
        return 1


class Command(BaseCommand):
    """
    This management command loops forever, checking for pending image upload jobs in the database.
    """

    help = "Check for pending image upload jobs in the DB and process them"

    def add_arguments(self, parser):
        parser.add_argument('-d', '--delete-jobs',
                            action="store_true",
                            default=False,
                            help='Delete all jobs with status == DONE')

    def handle(self, *args, **options):

        sleep_time = 1
        num_checks = 0

        if options['delete_jobs']:
            # DONE jobs should not have heavy image data anymore
            # so we can safely load a lot at once
            jobs = UploadImageJob.objects.filter(status=UploadImageJob.Status.DONE)[:MAX_JOBS_LOADED]
            jobs.delete()
            exit(1)

        while True:
            log.info(f"Checking for pending jobs every {sleep_time}s (it {num_checks})")

            if jobs := get_pending_jobs():
                log.info(f"Starting processing on {len(jobs)} job{'s' if len(jobs) > 1 else ''}")

                # Process all jobs, deleting successful ones
                for job in jobs:
                    try:
                        process_job(job)
                    except:
                        log.error(f"Error processing job {job.id}")
                        traceback.print_exc()
                        continue

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
