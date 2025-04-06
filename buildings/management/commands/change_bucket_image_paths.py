import re
import logging
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

    def handle(self, *args, **options):

        log_file = open(Path.cwd() / "notes/copy_images.log", "w", encoding="utf8")

        buildings = Building.objects.all()

        for bldg in buildings:

            for size in sizes:
                log_file.write(f"Processing {bldg.slug} {size}\n") 
                log.info(f"Processing {bldg.slug} {size}")

                original_prefix = f"reconstruct/{bldg.dataset.slug}/{size}/{bldg.slug}"
                new_prefix = f"reconstruct/{bldg.dataset.slug}/{bldg.slug}/{size}"
                

                prod_resp = prod_client.list_objects_v2(
                    Bucket=PROD_BUCKET, 
                    Prefix=original_prefix
                )
                # Check if keys at original location exist
                if not prod_resp["KeyCount"]:
                    log_file.write(f"\tNo keys in {original_prefix}\n")
                    log.info(f"\tNo keys in {original_prefix}")
                    continue

                resp = prod_client.list_objects_v2(
                    Bucket=PROD_BUCKET,
                    Prefix=new_prefix,
                )

                if resp["KeyCount"] == prod_resp["KeyCount"]:
                    log_file.write(f"\tAlready done. skipping\n")
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
                dest_thumbnail_key = f"reconstruct/{bldg.dataset.slug}/{bldg.slug}/thumbnail.jpg"

                prod_client.copy_object(
                    Bucket=PROD_BUCKET,
                    CopySource=thumbnail_key,
                    Key=dest_thumbnail_key,
                )
