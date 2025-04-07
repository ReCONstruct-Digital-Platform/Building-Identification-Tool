from datetime import datetime
import math
from multiprocessing import Pool
import os
import logging
import traceback

import django
from tqdm import tqdm
from buildings.models.newmodels import Building, Dataset
from buildings.utils import b2
from django.core.management.base import BaseCommand
from pathlib import Path


log = logging.getLogger(__name__)

from config.settings import B2_ENDPOINT, B2_BUCKET_IMAGES

PROD_KEY_ID = ""
PROD_APP_KEY = ""
PROD_BUCKET = "bit-prod"

prod_client = b2.get_b2_client(B2_ENDPOINT, PROD_KEY_ID, PROD_APP_KEY)

# current_client = b2_upload.get_client()


sizes = ["s", "m", "l"]

class Command(BaseCommand):
    """
    Mistakes were made - change the bucket image paths from <dataset>/<size>/<building> to <dataset>/<building>/<size>
    """
    def add_arguments(self, parser):
        parser.add_argument(
            "-n",
            "--num-workers",
            type=int,
            default=os.cpu_count() - 1,
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
                self.style.SUCCESS(f"Finished in {datetime.now() - t0} s")
            )

        except KeyboardInterrupt:
            self.stdout.write(self.style.ERROR("Interrupt received. Exiting."))
            exit()


def change_image_paths(split):

    worker_id = split["worker_id"]
    i_start = split["i_start"]
    i_stop = split["i_stop"]

    buildings = Building.objects.all().order_by("address")[i_start:i_stop]

    for i, bldg in enumerate(buildings):

        log.info(f"Worker {worker_id}: Processing {bldg.slug} ({i}/{i_stop - i_start})")

        for size in sizes:
            try:

                original_prefix = f"reconstruct/{bldg.dataset.slug}/{size}/{bldg.slug}"
                new_prefix = f"reconstruct/{bldg.dataset.slug}/{bldg.slug}/{size}"

                prod_resp = prod_client.list_objects_v2(
                    Bucket=PROD_BUCKET, Prefix=original_prefix
                )
                # Check if keys at original location exist
                if not prod_resp["KeyCount"]:
                    log.info(f"\tNo keys in {original_prefix}")
                    continue

                resp = prod_client.list_objects_v2(
                    Bucket=PROD_BUCKET,
                    Prefix=new_prefix,
                )

                if resp["KeyCount"] == prod_resp["KeyCount"]:
                    log.info(f"\tAlready done\n")
                    continue

                all_pics = prod_resp["Contents"]

                for pic in all_pics:
                    pic_key = pic["Key"]
                    src_key = f"{PROD_BUCKET}/{pic_key}"
                    pic_filename = pic_key.split("/")[-1]
                    dest_key = f"{new_prefix}/{pic_filename}"

                    prod_client.copy_object(
                        Bucket=PROD_BUCKET,
                        CopySource=src_key,
                        Key=dest_key,
                    )

                # Copy thumnbail as well
                thumbnail_key = f"{PROD_BUCKET}/reconstruct/{bldg.dataset.slug}/thumbnails/{bldg.slug}/thumbnail.jpg"
                dest_thumbnail_key = (
                    f"reconstruct/{bldg.dataset.slug}/{bldg.slug}/thumbnail.jpg"
                )

                prod_client.copy_object(
                    Bucket=PROD_BUCKET,
                    CopySource=thumbnail_key,
                    Key=dest_thumbnail_key,
                )

            except KeyboardInterrupt:
                return print("\n")
            except:
                print(traceback.format_exc())
                continue


def launch_jobs(num_workers, test=False):

    # Split the XMLs evenly between the workers
    splits = split_data_between_workers(num_workers, test=test)

    # Doesn't work without the initializer function
    # https://stackoverflow.com/questions/73295496/django-how-can-i-use-multiprocessing-in-a-management-command
    with Pool(processes=num_workers, initializer=django.setup) as pool:
        pool.map(change_image_paths, splits)


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
                    else (i * buildings_per_worker) + 500
                ),
            }
        )

    return splits
