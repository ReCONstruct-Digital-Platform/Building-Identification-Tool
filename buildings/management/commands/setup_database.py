
import os
import traceback

from tqdm import tqdm
from pathlib import Path
from datetime import datetime

from django.core.management import call_command
from django.core.management.base import BaseCommand
from config.settings import BASE_DIR

DEFAULT_OUT = BASE_DIR / 'data' 

ROLL_XML_COMMAND = 'process_roll_xml'
ROLL_SHP_COMMAND = 'process_roll_shp'

class Command(BaseCommand):
    help = "Setup the database by downloading and processing the roll XML data, the roll SHP data, aggregating MURBs and linking HLMs"

    def add_arguments(self, parser):
        parser.add_argument('-o', '--output-folder', 
                            type=Path, 
                            default=DEFAULT_OUT,
                            help='Directory containing the data, or where it will be downloaded.') 
        
        parser.add_argument('-d', '--download-data', 
                            action="store_true", 
                            default=False,
                            help="Download the data (~7GB)")
        
        parser.add_argument('-dd', '--delete-data', 
                            action="store_true", 
                            default=False,
                            help="Delete the data after processing (~7GB)")

        parser.add_argument('-n', '--num-workers', 
                            type=int, 
                            default=os.cpu_count() - 1, 
                            help="Number of parallel workers to use where applicable. Defaults to one less than the number of CPUs.")
        
        parser.add_argument('-t', '--test', 
                            action='store_true', 
                            default=False,
                            help="Run in testing mode (runs on a subset of files)")


    def handle(self, *args, **options):
        output_folder = options['output_folder']
        download_data = options['download_data']
        delete_data = options['delete_data']
        num_workers = options['num_workers']
        test = options['test']

        t0 = datetime.now()

        try:
            call_command('process_roll_xml', 
                        output_folder= output_folder, 
                        download_data=download_data, 
                        delete_data=delete_data, 
                        num_workers=num_workers, 
                        test=test)
            
            call_command('process_roll_shp', 
                        output_folder= output_folder,
                        num_workers=num_workers,
                        download_data=download_data, 
                        delete_data=delete_data, 
                        test=test)
            
            call_command('aggregate_murbs', 
                        num_workers=num_workers, 
                        test=test)
            
            call_command('process_lots', 
                        output_folder= output_folder,
                        download_data=download_data, 
                        delete_data=delete_data, 
                        test=test)
            
            call_command('crossref_hlms', 
                        output_folder= output_folder,
                        download_data=download_data, 
                        delete_data=delete_data, 
                        num_workers=num_workers, 
                        test=test)
            
            call_command('check_streetview', 
                        num_workers=num_workers)
            
            self.stdout.write(
                self.style.SUCCESS(f'\nFinished setting up DB in {datetime.now() - t0} s')
            )
        
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.ERROR('\nInterrupt received')
            )

        except:
            self.stdout.write(
                self.style.ERROR('ERROR')
            )
            self.stdout.write(
                self.style.ERROR(traceback.format_exc())
            )