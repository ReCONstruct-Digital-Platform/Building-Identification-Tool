import re
import logging
from buildings.models.newmodels import Building, Dataset
from buildings.utils import b2_upload
from django.core.management.base import BaseCommand
from pathlib import Path


log = logging.getLogger(__name__)

from config.settings import B2_ENDPOINT

PROD_KEY_ID = "005ca66e26262c30000000002"
PROD_APP_KEY = "K005ICKiDp5wkCsXlxoxUABUUv3zibE"

b2 = b2_upload.get_b2_resource(B2_ENDPOINT, PROD_KEY_ID, PROD_APP_KEY)
prod_client = b2_upload.get_b2_client(B2_ENDPOINT, PROD_KEY_ID, PROD_APP_KEY)


class Command(BaseCommand):
    """
    One-off script to migrate thumbnails in B2 from old scheme to new one
    """

    def handle(self, *args, **options):

        log_file = open(Path.cwd() / "notes/create_thumbnail.log", "w", encoding="utf8")

        ds_metal = Dataset.objects.get(name='Potential Metal Buildings')

        metal_buildings = Building.objects.filter(dataset=ds_metal)

        for metal_building in metal_buildings:

            address = metal_building.address
            eval_unit_id = metal_building.attrs["eval_unit_id"]

            log_file.write(f"Processing {eval_unit_id} - {address}\n")
            log.info(f"Processing {eval_unit_id} - {address}")

            resp = prod_client.list_objects_v2(
                Bucket="bit-prod",
                Prefix=f"reconstruct/{ds_metal.slug}/thumbnails/{metal_building.slug}",
            )

            if resp["KeyCount"]:
                log_file.write(f"\tAlready done. skipping\n")
                log.info(f"\tAlready done\n")
                continue

            # no other id for metal buildings, it's either there or not
            pics_dir = eval_unit_id

            resp = prod_client.list_objects_v2(
                Bucket="bit-prod", Prefix=f"metal/{pics_dir}"
            )

            if not resp["KeyCount"]:
                log_file.write(f"No dirs found for {eval_unit_id} - {address}\n")
                log.info(f"No dirs found for {eval_unit_id} - {address}")
                continue

            all_pics = resp["Contents"]

            small_pics = [p for p in all_pics if f"/s/" in p["Key"]]

            if not small_pics:
                log_file.write(f"No /s/ subfolder found under metal/{pics_dir}\n")
                log.warning(f"No /s/ subfolder found under metal/{pics_dir}")
                continue
            
            # Arbitrarily take the first small pic as the thumbnail
            thumbnail_key = [
                p["Key"] for p in all_pics if f"/s/{pics_dir}_0" in p["Key"]
            ]

            if not thumbnail_key:
                thumbnail_key = [
                    p["Key"] for p in all_pics if f"/s/{pics_dir}" in p["Key"]
                ]

            if not thumbnail_key:
                thumbnail_key = [p["Key"] for p in all_pics if f"/s/" in p["Key"]]

            if not thumbnail_key:
                thumbnail_key = [p["Key"] for p in all_pics]

            thumbnail_key = thumbnail_key[0]

            src_key = f"bit-prod/{thumbnail_key}"
            dest_key = f"reconstruct/{ds_metal.slug}/thumbnails/{metal_building.slug}/thumbnail.jpg"

            # Copy the first file to thumbnail dir
            prod_client.copy_object(
                Bucket="bit-prod",
                CopySource=src_key,
                Key=dest_key,
            )

            log_file.write(f"Thumbnail created: {src_key} to {dest_key}\n")
            log.info(f"Thumbnail created: {src_key} to {dest_key}")

            # regex to extract the file size category
            pattern = re.compile(r"metal/[0-9_]+/([sml])/*")

            log_file.write(f"Copying all pics:\n")
            log.info(f"Copying all pics:")

            # Keep track of the number the image index by size
            i_sizes = {"s": 0, "m": 0, "l": 0}

            for i, pic in enumerate(all_pics):

                pic_key = pic["Key"]
                size = re.match(pattern, pic_key).group(1)

                i_sizes[size] += 1

                src_key = f"bit-prod/{pic_key}"
                dest_key = (
                    f"reconstruct/{ds_metal.slug}/{size}/{metal_building.slug}/{i_sizes[size]}.jpg"
                )

                prod_client.copy_object(
                    Bucket="bit-prod",
                    CopySource=src_key,
                    Key=dest_key,
                )

                log_file.write(f"\tCopied {pic_key} to {dest_key}\n")
                log.info(f"\tCopied {pic_key} to {dest_key}")

            log_file.write(f"Copied {i+1} pics\n")
            log.info(f"Copied {i+1} pics")
