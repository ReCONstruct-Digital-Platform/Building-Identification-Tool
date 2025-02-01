import re
import logging
from buildings.models.newmodels import Building, Dataset
from buildings.utils import b2_upload
from django.core.management.base import BaseCommand
from pathlib import Path


log = logging.getLogger(__name__)

from config.settings import B2_ENDPOINT

PROD_KEY_ID = ""
PROD_APP_KEY = ""

b2 = b2_upload.get_b2_resource(B2_ENDPOINT, PROD_KEY_ID, PROD_APP_KEY)
prod_client = b2_upload.get_b2_client(B2_ENDPOINT, PROD_KEY_ID, PROD_APP_KEY)


class Command(BaseCommand):
    """
    One-off script to migrate thumbnails in B2 from old scheme to new one
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "-d",
            "--delete-jobs",
            action="store_true",
            default=False,
            help="Delete all jobs with status == DONE",
        )

    def handle(self, *args, **options):

        log_file = open(Path.cwd() / "notes/create_thumbnail.log", "w", encoding="utf8")

        ds_hlm = Dataset.objects.get(name="SHQ HLMs")

        hlms = Building.objects.filter(dataset=ds_hlm)

        for hlm in hlms:

            hlm_id = hlm.ext_id
            eval_unit_id = hlm.attrs["eval_unit_id"]

            log_file.write(f"Processing {eval_unit_id} - {hlm_id}\n")
            log.info(f"Processing {eval_unit_id} - {hlm_id}")

            resp = prod_client.list_objects_v2(
                Bucket="bit-prod",
                Prefix=f"reconstruct/{ds_hlm.slug}/thumbnails/{hlm.slug}",
            )

            if resp["KeyCount"]:
                log_file.write(f"\tAlready done. skipping\n")
                log.info(f"\tAlready done\n")
                continue

            # try the most specific first
            pics_dir = f"{eval_unit_id}_{hlm_id}"

            resp = prod_client.list_objects_v2(
                Bucket="bit-prod", Prefix=f"hlms/{pics_dir}"
            )

            if not resp["KeyCount"]:

                # Try the overall dir
                pics_dir = eval_unit_id

                resp = prod_client.list_objects_v2(
                    Bucket="bit-prod", Prefix=f"hlms/{pics_dir}"
                )

            if not resp["KeyCount"]:
                log_file.write(f"No dirs found for {eval_unit_id} - {hlm_id}\n")
                log.info(f"No dirs found for {eval_unit_id} - {hlm_id}")
                continue

            all_pics = resp["Contents"]

            small_pics = [p for p in all_pics if f"/s/" in p["Key"]]

            if not small_pics:
                log_file.write(f"No /s/ subfolder found under hlms/{pics_dir}\n")
                log.warning(f"No /s/ subfolder found under hlms/{pics_dir}")
                continue

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
            dest_key = f"reconstruct/{ds_hlm.slug}/thumbnails/{hlm.slug}/thumbnail.jpg"

            # Copy the first file to thumbnail dir
            prod_client.copy_object(
                Bucket="bit-prod",
                CopySource=src_key,
                Key=dest_key,
            )

            log_file.write(f"Thumbnail created: {src_key} to {dest_key}\n")
            log.info(f"Thumbnail created: {src_key} to {dest_key}")

            # regex to extract the file size category
            pattern = re.compile(r"hlms/[0-9_]+/([sml])/*")

            log_file.write(f"Copying all pics:\n")
            log.info(f"Copying all pics:")

            # Divide the pics in small medium large sizes first

            i_sizes = {"s": 0, "m": 0, "l": 0}

            for i, pic in enumerate(all_pics):

                pic_key = pic["Key"]
                size = re.match(pattern, pic_key).group(1)

                i_sizes[size] += 1

                src_key = f"bit-prod/{pic_key}"
                dest_key = (
                    f"reconstruct/{ds_hlm.slug}/{size}/{hlm.slug}/{i_sizes[size]}.jpg"
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
