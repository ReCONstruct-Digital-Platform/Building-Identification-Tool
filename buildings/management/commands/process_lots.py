import os
import math
import subprocess
import traceback

from tqdm import tqdm
from pathlib import Path
from datetime import datetime
from django.db import connection
from buildings.models import EvalUnit
from django.core.management.base import BaseCommand
from buildings.models.models import EvalUnitLot
from buildings.utils.utility import download_file, get_DB_conn

from config.settings import BASE_DIR

DEFAULT_OUT = BASE_DIR / "data"

EVALUNIT_TABLE = EvalUnit.objects.model._meta.db_table
LOTS_TABLE = EvalUnitLot.objects.model._meta.db_table
LOTS_TABLE_TMP = "lots_tmp"

DB_NAME = connection.settings_dict["NAME"]
DB_HOST = connection.settings_dict["HOST"]
DB_PORT = connection.settings_dict["PORT"]
DB_USER = connection.settings_dict["USER"]
DB_PW = connection.settings_dict["PASSWORD"]
DB_CONN_STR = f"postgresql://{DB_USER}:{DB_PW}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


class Command(BaseCommand):
    help = "Process the roll data and fill the database."

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
            help="Download the data (~4.5GB). Automatically done if data can't be found.",
        )

        parser.add_argument(
            "-dd",
            "--delete-data",
            action="store_true",
            default=False,
            help="Delete the data after processing (~4.5GB)",
        )

        parser.add_argument(
            "-t",
            "--test",
            action="store_true",
            default=False,
            help="Run in testing mode (process only a few data points)",
        )

        parser.add_argument(
            "-si",
            "--skip-import",
            action="store_true",
            default=False,
            help="Do not import the shapes (i.e. if they were already imported)",
        )

    def handle(self, *args, **options):

        data_folder: Path = options["output_folder"]

        roll_shp_folder = data_folder / Path("roll_shp")
        roll_shp_folder.mkdir(exist_ok=True, parents=True)

        download_data = options["download_data"]
        delete_data = options["delete_data"]
        skip_import = options["skip_import"]
        test = options["test"]

        t0 = datetime.now()
        # Now process the lot polygons shapefile
        lots_shp_folder = data_folder / Path("lots_shp")
        lots_shp_folder.mkdir(exist_ok=True, parents=True)

        try:
            if not skip_import:

                # Search the data directory for the lots shapefile
                if (
                    not list(lots_shp_folder.glob("**/usage_predominant_s_2022.shp"))
                    or download_data
                ):
                    download_file(
                        "https://f005.backblazeb2.com/file/bit-data-public/quebec_lots_shapefiles.zip",
                        lots_shp_folder,
                        unzip=True,
                    )
                    self.stdout.write(
                        self.style.SUCCESS(
                            "Lot polygon shapefile downloaded successfully"
                        )
                    )
                self.stdout.write(
                    self.style.SUCCESS(
                        "\nImporting the lots polygons... This will take a few minutes.\n\n"
                    )
                )

                # Archive contains 2 SHP files due to a max size limitation on shapefiles
                # https://gis.stackexchange.com/questions/312739/why-are-shapefiles-limited-to-2gb-in-size
                filenames = [
                    "usage_predominant_s_2022.shp",
                    "usage_predominant_s_2022_1.shp",
                ]
                if test:
                    filenames = [filenames[0]]

                # Creates a temporary table for the lots.
                # PATH needs to contain the shp2pgsql program.
                # Should be installed with PostGIS, but maybe not put on PATH.
                # See https://postgis.net/docs/using_postgis_dbmanagement.html#shp2pgsql_usage
                cmds = [
                    f"shp2pgsql -D {'-a' if i > 0 else '-c'} -s 3857:4326 {lots_shp_folder}/{filename} {LOTS_TABLE_TMP} | psql -q {DB_CONN_STR}"
                    for i, filename in enumerate(filenames)
                ]
                for cmd in cmds:
                    subprocess.check_call(cmd, shell=True)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Finished importing lots to temporary table in {datetime.now() - t0}s"
                    )
                )

                # Delete street lots
                count = delete_lots_without_cubf()
                self.stdout.write(
                    self.style.SUCCESS(f"Deleted {count} lots that did not have a CUBF")
                )

                migrate_to_real_table()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Finshed cleaning data and transfered to final lots table"
                    )
                )

            # Now we will go through the lots and attempt to link each one to an evaluation unit
            # Here we can also simplify the polygons
            t0 = datetime.now()
            link_lots_to_evalunits(self, delete_data=delete_data, test=test)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Finished processing lots in {datetime.now() - t0}s"
                )
            )

            if delete_data and not test:
                for filename in filenames:
                    os.remove(f"{lots_shp_folder}/{filename}")
                    print(f"Deleted {lots_shp_folder}/{filename}")

        except KeyboardInterrupt:
            self.stdout.write(self.style.ERROR("Interrupt received"))
            exit()

        except:
            self.stdout.write(traceback.format_exc())
            self.stdout.write(self.style.ERROR("Error running command"))


def migrate_to_real_table():
    conn, cursor = get_DB_conn(DB_CONN_STR, dict_cursor=False)
    # Ignore the gid, we'll have our own autoincrement primary key in the lots table
    # as we're going to duplicate some of these lots
    cursor.execute(f"UPDATE {LOTS_TABLE_TMP} SET gid = objectid where gid is null;")
    cursor.execute(
        f"""
                   INSERT INTO {LOTS_TABLE} SELECT 
                    gid, objectid, co_mrc, code_mun, arrond, anrole, usag_predo, 
                    no_lot, nb_poly_lo, utilisatio, id_provinc, sup_totale, descriptio, 
                    nb_logemen, nb_locaux, shape_leng, shape_area, dat_acqui, dat_charg,
                    --- Simplify the polygons to reduce their size
                    st_simplify(geom, 0.000005, true) as geom
                   FROM {LOTS_TABLE_TMP} ON CONFLICT DO NOTHING"""
    )
    cursor.execute(f"DROP TABLE {LOTS_TABLE_TMP}")
    conn.commit()


def delete_lots_without_cubf():
    """
    Delete lots without an 'utilisatio' (CUBF) field.
    These seem to be associatd with streets, so we don't care about them.
    This runs before we associate evalunits to lots, so it can speed up the matching.
    """
    conn, cursor = get_DB_conn(DB_CONN_STR, dict_cursor=False)
    cursor.execute(f"SELECT count(*) FROM {LOTS_TABLE_TMP} WHERE utilisatio IS null")
    count = cursor.fetchone()[0]

    cursor.execute(f"DELETE FROM {LOTS_TABLE_TMP} WHERE utilisatio IS null")
    conn.commit()

    cursor.execute(f"SELECT count(*) FROM {LOTS_TABLE_TMP} WHERE utilisatio IS null")
    assert cursor.fetchone()[0] == 0

    return count


def link_lots_to_evalunits(self, delete_data=False, test=False):
    """
    Chose not to parallelize this as we're doing lots of quick writing to the DB.
    """
    self.stdout.write("\nLinking lots to evaluation units...")
    conn, cursor = get_DB_conn(DB_CONN_STR, dict_cursor=False)

    # In an attempt to speed up the following operations
    cursor.execute(f"SELECT count(*) FROM {LOTS_TABLE};")
    num_lots = cursor.fetchone()[0]

    NUM_CHUNKS = 100 if not test else 2

    chunk_length = math.ceil(num_lots / NUM_CHUNKS)

    progress_bar = tqdm(total=num_lots, desc=f"Processing lots")

    # Split lots into 100 chunks
    # The whole table is about 4GB so each chunk will be ~40MB and can be loaded in memory easily
    # Donig the whole operation in the DB took a long time and we had no visibility on progress

    # We simplify the geometries here using st_simplify(geom, 0.000005, true)
    # because drawing some of them on the streetview was getting expensive
    for offset in range(0, num_lots, chunk_length):

        # ORDER BY clause is required to guarantee sequentiality of pages when using limit and offset
        # https://www.postgresql.org/docs/current/queries-limit.html
        cursor.execute(
            f"SELECT gid, id_provinc FROM {LOTS_TABLE} ORDER BY gid DESC LIMIT {chunk_length} OFFSET {offset};"
        )
        lots = cursor.fetchall()

        for i, lot in enumerate(lots):
            gid, id_provinc = lot

            # For lots without a single provincial ID (there are at least 30233),
            # do a spatial intersection search to find the associated eval units
            if id_provinc == "Multiple":
                cursor.execute(
                    f"""
                        UPDATE {EVALUNIT_TABLE} AS e 
                        SET lot_id = %s 
                        FROM (
                            SELECT e.id as id
                            FROM lots l 
                            JOIN evalunits e ON ST_Intersects(l.geom, e.point) 
                            WHERE l.gid = %s 
                        ) AS r WHERE r.id = e.id;""",
                    (gid, gid),
                )

            # For lots with a single provincial ID, simply retrieve the evaluation unit
            else:
                cursor.execute(
                    f"""
                               UPDATE {EVALUNIT_TABLE} 
                               SET lot_id = %s
                               WHERE id = %s
                               """,
                    (gid, id_provinc),
                )
            progress_bar.update(1)

            if i % 10_000:
                conn.commit()

    self.stdout.write(self.style.SUCCESS("\nDone"))
