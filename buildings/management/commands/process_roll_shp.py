import math
from multiprocessing import Pool
import os
import shutil
import IPython
import traceback
import django
import shapefile

from tqdm import tqdm
from pathlib import Path
from datetime import datetime
from django.db.models import Q
from django.db import connection
from config.settings import BASE_DIR
from buildings.models import EvalUnit
from django.core.management.base import BaseCommand
from buildings.utils.utility import download_file, is_streetview_imagery_available

DEFAULT_OUT = BASE_DIR / "data"

EVALUNIT_TABLE = EvalUnit.objects.model._meta.db_table


class Command(BaseCommand):
    help = "Process the roll shapefile to add coordinates to the evaluation units."

    def add_arguments(self, parser):
        parser.add_argument(
            "-o",
            "--output-folder",
            type=Path,
            default=DEFAULT_OUT,
            help="Path to folder containing the roll data, or where it will be downloaded.",
        )

        parser.add_argument(
            "-d",
            "--download-data",
            action="store_true",
            default=False,
            help="Download the data (~2GB). Automatically done if data can't be found.",
        )

        parser.add_argument(
            "-n",
            "--num-workers",
            type=int,
            default=os.cpu_count() - 1,
            help="Number of parallel workers. Defaults to one less than the number of CPUs.",
        )

        parser.add_argument(
            "-dd",
            "--delete-data",
            action="store_true",
            default=False,
            help="Delete the data after processing (~2GB)",
        )

        parser.add_argument(
            "-t",
            "--test",
            action="store_true",
            default=False,
            help="Run in testing mode (won't delete units without coords after)",
        )

    def handle(self, *args, **options):

        data_folder: Path = options["output_folder"]

        roll_shp_folder = data_folder / Path("roll_shp")
        roll_shp_folder.mkdir(exist_ok=True, parents=True)

        download_data = options["download_data"]
        delete_data = options["delete_data"]
        num_workers = options["num_workers"]
        test = options["test"]

        t0 = datetime.now()

        # Search the data directory for the shapefile
        if not list(roll_shp_folder.glob("**/rol_unite_p.shp")) or download_data:
            download_file(
                "https://donneesouvertes.affmunqc.net/role/ROLE2022_SHP.zip",
                roll_shp_folder,
                unzip=True,
            )
            self.stdout.write(
                self.style.SUCCESS("Roll points shapefile downloaded successfully")
            )

        shp_file = next(roll_shp_folder.glob("**/rol_unite_p.shp"))

        try:
            launch_jobs(shp_file, num_workers, test=test)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Finished parsing shapefile in {datetime.now() - t0} s"
                )
            )
            if not test:
                count = cleanup_entries_without_coords()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Cleaned up {count} entries without coordinates"
                    )
                )
        except KeyboardInterrupt:
            self.stdout.write(self.style.ERROR("Interrupt received. Exiting."))
            exit()
        finally:
            if delete_data:
                shutil.rmtree(data_folder)
                self.stdout.write(self.style.SUCCESS("Removed the downloaded data"))


def launch_jobs(shp_file, num_workers, test=False):

    # Split the XMLs evenly between the workers
    splits = split_data_between_workers(shp_file, num_workers, test=test)

    # Doesn't work without the initializer function
    # https://stackoverflow.com/questions/73295496/django-how-can-i-use-multiprocessing-in-a-management-command
    with Pool(processes=num_workers, initializer=django.setup) as pool:
        pool.map(parse_shapefile, splits)


def split_data_between_workers(shp_file, num_workers, test=False):
    # Get the total number of cases, and divide per worker
    with shapefile.Reader(shp_file) as shp:
        num_units = len(shp)
    units_per_worker = math.ceil(num_units / num_workers)

    # Assign each worker a start and stop index for their part of the work
    splits = []
    for i in range(num_workers):
        splits.append(
            {
                "worker_id": i,
                "file": shp_file,
                "i_start": i * units_per_worker,
                "i_stop": (
                    (i + 1) * units_per_worker
                    if not test
                    else (i * units_per_worker) + 500
                ),
            }
        )

    return splits


def parse_shapefile(split, test=False):
    """
    Parse part of the roll shapefile, adding coordinates to all
    eval units that have streetview imagery available for them.
    """
    worker_id = split["worker_id"]
    i_start = split["i_start"]
    i_stop = split["i_stop"]
    shp_file = split["file"]

    # This curosr will handle commiting transactions
    with shapefile.Reader(shp_file) as shp, connection.cursor() as cursor:

        if test:
            num_units = 500
        else:
            num_units = i_stop - i_start

        progress_bar = tqdm(
            total=num_units, desc=f"Worker {worker_id}", position=worker_id, leave=False
        )
        for i in range(i_start, i_stop):
            try:
                # The ID field is globally unique for evaluation units
                id = shp.record(i)[0]

                # We don't need to transform the coordinates, the point
                # has lat/lng in NAD83 which is compatbile with WSG84.
                # In QGIS, changing the CRS from NAD83 to WDG84 performs the EPSG-1188
                # transformation, which we see here https://epsg.io/1188 is a noop.
                lng, lat = shp.shape(i).points[0]

                # Check if streetview imagery is available and skip if not
                cursor.execute(
                    f"""
                    UPDATE {EVALUNIT_TABLE} 
                    SET
                        lng = %s,
                        lat = %s,
                        point = ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                        WHERE id = %s
                """,
                    [lng, lat, lng, lat, id],
                )

                # Update the progress bar every 100 so it's less buggy with multiple parallel process
                if (i - i_start) % 100 == 0 and (i - i_start) > 0:
                    progress_bar.update(100)

            except KeyboardInterrupt:
                return print("\n")
            except IndexError:
                return
            except:
                print(traceback.format_exc())
                continue


def cleanup_entries_without_coords():
    """
    Delete all entries for which we do not have coordinates
    """
    count = EvalUnit.objects.filter(Q(lat=None) | Q(lng=None)).count()
    EvalUnit.objects.filter(Q(lat=None) | Q(lng=None)).delete()
    assert EvalUnit.objects.filter(Q(lat=None) | Q(lng=None)).count() == 0
    return count
