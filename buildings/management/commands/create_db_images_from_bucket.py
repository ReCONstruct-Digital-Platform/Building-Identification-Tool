from datetime import datetime
import math
from multiprocessing import Pool
import io
import logging
import traceback

import botocore
import django
from tqdm import tqdm
from buildings.models.models import BuildingImage
from buildings.models.newmodels import Building, Dataset
from buildings.utils import b2
from django.core.management.base import BaseCommand
from pathlib import Path


log = logging.getLogger(__name__)

from config.settings import B2_BUCKET_IMAGES


b2client = b2.get_client()

class Command(BaseCommand):
    """
    Mistakes were made - change the bucket image paths from <dataset>/<size>/<building> to <dataset>/<building>/<size>
    """
    def add_arguments(self, parser):
        parser.add_argument(
            "-n",
            "--num-workers",
            type=int,
            default=1,
            help="Number of parallel workers. Defaults to one less than the number of CPUs.",
        )
        parser.add_argument(
            "-t",
            "--test",
            action="store_true",
            default=False,
            help="Run in testing mode (will use a few cases only)",
        )

    def handle(self, *args, **options):

        t0 = datetime.now()
        num_workers = options["num_workers"]
        test = options["test"]

        try:
            launch_jobs(num_workers, test=test)
            self.stdout.write(
                self.style.SUCCESS(f"Finished ALL in {datetime.now() - t0} s")
            )

        except KeyboardInterrupt:
            self.stdout.write(self.style.ERROR("Interrupt received. Exiting."))
            exit()


def create_db_images_from_bucket(split):
    """
    Only need to list for one image size.
    Create the DB object for each image seen in bucket
    """

    worker_id = split["worker_id"]
    i_start = split["i_start"]
    i_stop = split["i_stop"]

    buildings = Building.objects.all().order_by("address")[i_start:i_stop]

    for i, bldg in enumerate(buildings):

        log.info(f"Worker {worker_id}: {bldg.slug} ({i}/{i_stop - i_start})")

        try:
            prefix = f"reconstruct/{bldg.dataset.slug}/{bldg.slug}/l"

            resp = b2client.list_objects_v2(
                Bucket=B2_BUCKET_IMAGES, Prefix=prefix
            )
            if not resp["KeyCount"]:
                log.info(f"\tNo keys in {prefix}")
                continue

            all_pics = resp["Contents"]

            for pic in all_pics:
                pic_key = pic["Key"]
                filename = pic_key.split("/")[-1]
                image_type = "sat" if "sat" in filename else "sv"
                # Check if the image already exists in the DB
                if BuildingImage.objects.filter(
                    building=bldg, filename=filename
                ).exists():
                    log.info(f"\tAlready exists: {filename}")
                    continue
                else:

                    head_obj_result = b2client.head_object(Bucket=B2_BUCKET_IMAGES, Key=pic_key)

                    BuildingImage(
                        building=bldg,
                        filename=filename,
                        type=image_type,
                        metadata=head_obj_result["Metadata"] if "Metadata" in head_obj_result else {},
                    ).save()


        except KeyboardInterrupt:
            return print("\n")
        except:
            print(traceback.format_exc())
            continue


def launch_jobs(num_workers, test=False):

    # Don't use multiprocessing in test mode
    if test:
        create_db_images_from_bucket(
            {
                "worker_id": 0,
                "i_start": 0,
                "i_stop": 10,
            }
        )
        return

    # Split the XMLs evenly between the workers
    splits = split_data_between_workers(num_workers, test=test)

    # Doesn't work without the initializer function
    # https://stackoverflow.com/questions/73295496/django-how-can-i-use-multiprocessing-in-a-management-command
    with Pool(processes=num_workers, initializer=django.setup) as pool:
        pool.map(create_db_images_from_bucket, splits)


def split_data_between_workers(num_workers, test=False):

    num_buildings = Building.objects.all().count()
    buildings_per_worker = math.ceil(num_buildings / num_workers)

    # Assign each worker a start and stop index for their part of the work
    splits = []
    for i in range(num_workers):
        splits.append(
            {
                "worker_id": i,
                "i_start": i * buildings_per_worker,
                "i_stop": (
                    (i + 1) * buildings_per_worker
                    if not test
                    else (i * buildings_per_worker) + 1
                ),
            }
        )

    return splits
