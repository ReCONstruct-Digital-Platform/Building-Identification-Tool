import os
import time
import heapq
import shutil
from xml.sax import SAXParseException
import django
import IPython
import traceback
import pandas as pd

from tqdm import tqdm
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from django.db.models import Q
from multiprocessing import Pool
from xml.dom.pulldom import parse
from django.core.management.base import BaseCommand

from buildings.models import EvalUnit, CUBF
from buildings.utils.utility import sizeof_fmt, download_file
from buildings.utils.constants import * 

from config.settings import BASE_DIR

DEFAULT_OUT = BASE_DIR / 'data' 

# A subset of all CUBFs that includes residential units and 
# units likely to contain metal prefab buildings.
# If this list evolves in the future, we could rerun this command with 
# only the new CUBFs - the rest of the workflow would have to be adapted slightly.
CUBFS_TO_KEEP = set([
    1000, 1511, 1512, 1521, 1522, 1541, 1543, 1551, 1553, 1590, 2799, 5001, 5010, 5712, 5811, 5812, 6241, 6299, 6379, 6411, 6419, 6516, 6519, 6531, 6532, 6534, 6539, 6541, 6542, 6643, 6713, 6722, 6811, 6812, 6812, 6813, 6814, 6815, 6816, 6816, 6821, 6823, 6911, 6994, 6997, 6999, 7116, 7219, 7221, 7222, 7223, 7224, 7225, 7229, 7233, 7239, 7290, 7311, 7312, 7313, 7314, 7392, 7393, 7394, 7395, 7396, 7397, 7399, 7411, 7412, 7413, 7414, 7415, 7416, 7417, 7418, 7419, 7421, 7422, 7423, 7424, 7425, 7425, 7429, 7431, 7432, 7433, 7441, 7442, 7443, 7444, 7445, 7446, 7447, 7448, 7449, 7451, 7452, 7459, 7491, 7492, 7493, 7499, 7611, 9100, 9530
])

class Command(BaseCommand):
    help = "Download the roll data and fill the database"

    def add_arguments(self, parser):
        parser.add_argument('-o', '--output-folder', 
                            type=Path, 
                            default=DEFAULT_OUT,
                            help='Path to folder containing the roll data, or where it will be downloaded.') 
        
        parser.add_argument('-d', '--download-data', 
                            action="store_true", 
                            default=False,
                            help="Download the roll data (~5GB)")

        parser.add_argument('-dd', '--delete-data', 
                            action="store_true", 
                            default=False,
                            help="Delete the roll data after processing (~5GB)")
        
        parser.add_argument('-n', '--num-workers', 
                            type=int, 
                            default=os.cpu_count() - 1, 
                            help="Number of parallel workers. Defaults to one less than the number of CPUs.")
        
        parser.add_argument('-t', '--test', 
                            action='store_true', 
                            default=False,
                            help='Run in testing mode on a few XMLs')

    def handle(self, *args, **options):

        data_folder: Path = options['output_folder'] / Path('roll_xml')
        data_folder.mkdir(exist_ok=True, parents=True)

        download_data = options['download_data']
        delete_data = options['delete_data']
        num_workers = options['num_workers']
        test = options['test']
        
        t0 = datetime.now()

        if not list(data_folder.glob('**/CUBF_MEFQ.xlsx')) or download_data:
            download_file('https://www.mamh.gouv.qc.ca/fileadmin/publications/evaluation_fonciere/manuel_evaluation_fonciere/CUBF_MEFQ.xlsx', data_folder)
        process_cubfs(data_folder)

        # If the folder is empty
        if not list(data_folder.glob('**/*.xml')) or download_data:
            download_file("https://donneesouvertes.affmunqc.net/role/Roles_Donnees_Ouvertes_2022.zip", data_folder, unzip=True)

        try:
            launch_jobs(data_folder, num_workers, test=test)
            self.stdout.write(
                self.style.SUCCESS(f'\nFinished parsing XMLs in {datetime.now() - t0} s')
            )
            self.stdout.write(
                self.style.SUCCESS(f'Total units saved: {EvalUnit.objects.count()}')
            )
            num_deleted = delete_units_without_street_numbers()
            self.stdout.write(
                self.style.SUCCESS(f'Deleted {num_deleted} units without street numbers')
            )

        except KeyboardInterrupt:
            self.stdout.write(
                self.style.ERROR('\nInterrupt received')
            )
        finally:
            if delete_data:
                shutil.rmtree(data_folder)


def process_cubfs(data_folder):
    file = next(data_folder.glob('**/CUBF_MEFQ.xlsx'))
    df = pd.read_excel(file, skiprows=[0])
    for _, row in df.iterrows():
        if len(str(row['CUBF'])) == 4:
            cubf = CUBF(cubf=row['CUBF'], desc=row['DESCRIPTION'])
            cubf.save()
    

def delete_units_without_street_numbers():
    """
    Remove units that are missing inferior and superior street numbers,
    i.e. they refer to a street or other structure that we're not interested in.
    """
    count = EvalUnit.objects.filter(Q(num_adr_inf=None) & Q(num_adr_sup=None)).count()
    EvalUnit.objects.filter(Q(num_adr_inf=None) & Q(num_adr_sup=None)).delete()
    # Ensure there are no more units without street numbers
    assert EvalUnit.objects.filter(Q(num_adr_inf=None) & Q(num_adr_sup=None)).count() == 0
    return count


def launch_jobs(data_folder: Path, num_workers: int, test: bool = False):

    # Split the XMLs evenly between the workers
    splits = split_xmls_between_workers(data_folder, num_workers, test=test)

    # Doesn't work without the initializer function
    # https://stackoverflow.com/questions/73295496/django-how-can-i-use-multiprocessing-in-a-management-command
    with Pool(processes=num_workers, initializer=django.setup) as pool:
        pool.map(parse_xmls, splits)


def split_xmls_between_workers(data_folder: Path, num_workers: int, test: bool = False):
    """
    Partition the XMLs such that each worker has an approximately equal
    total data size to process. This is because some municipalities (i.e. Montreal)
    have vastly more data than others, and we want to parallelize as best as possible.
    """

    size_per_file = {}
    for xml_file in data_folder.glob('**/*.xml'):
        size_per_file[xml_file] = xml_file.stat().st_size

    # For the real run, sort the files by size in descending order
    size_per_file = dict(sorted(size_per_file.items(), key=lambda x: x[1], reverse=True))
    
    # For testing only, invert the sort order so smaller files are first
    # and truncate it to keep only a few files per worker.
    if test:
        import itertools
        size_per_file = dict(sorted(size_per_file.items(), key=lambda x: x[1]))
        size_per_file = dict(itertools.islice(size_per_file.items(), num_workers * 10, num_workers * 30))
        print(f'Truncated the input XMLs to {len(size_per_file)}')

    # We iterate over the files, starting from the one with largest
    # file size and distribute them among workers, always giving 
    # the current to the worker with the least amount of data.
    # Using a min heap, we quickly get the worker with the least amount of data.
    # https://stackoverflow.com/questions/61648065/split-list-into-n-sublists-with-approximately-equal-sums
    splits = [{'id': i + 1, 'files': [], 'size': 0} for i in range(num_workers)]
    worker_heap = [ [0, worker_id] for worker_id in range(num_workers)]
    heapq.heapify(worker_heap)

    # Pop a first worker from the heap
    lowest_worker = heapq.heappop(worker_heap)
    for file, size in size_per_file.items():
        # Get the worker's id
        worker_id = lowest_worker[1]
        # Add the file to the worker's split
        splits[worker_id]['files'].append(file)
        splits[worker_id]['size'] += size
        # Add the file size to the worker's total size
        lowest_worker[0] += size
        # Push back the worker and pop the new lowest
        lowest_worker = heapq.heappushpop(worker_heap, lowest_worker)
    
    # Print out results
    for split in splits:
        print(f"Worker {split['id']} will process {sizeof_fmt(split['size'])} in {len(split['files'])} files")

    return splits


            
def parse_xmls(work_split):

    worker_id = work_split['id']
    xml_files = work_split['files']
    worker_total_size = work_split['size']

    worker_total_units = 0
    progress_bar = tqdm(total=worker_total_size, desc=f"Worker {worker_id}", position=worker_id, 
                        unit='iB', unit_scale=True, unit_divisor=1024, leave=False)

    for xml_file in xml_files:
        try:
            # We use a streaming XML API for memory efficiency
            # Reading the whole file to build a BeautifulSoup object from it was too much
            event_stream = parse(str(xml_file))
            last_offset = 0

            # Get the municipal code and year entered first
            # Those are applicable to the whole document
            for i, (evt, node) in enumerate(event_stream):
                if evt == 'START_ELEMENT':
                    if node.tagName == 'RLM01A':
                        event_stream.expandNode(node)
                        muni_code = node.childNodes[0].nodeValue

                    if node.tagName == 'RLM02A':
                        event_stream.expandNode(node)
                        year_entered = node.childNodes[0].nodeValue
                        break
            
            current_units = []
            
            # Go through all the RLUEx tags - each represents a unit
            for j, (evt, node) in enumerate(event_stream):

                try:
                    if evt == 'START_ELEMENT':
                        if node.tagName == 'RLUEx':
                            # Parse until the closing tag
                            event_stream.expandNode(node)
                            unit_xml = BeautifulSoup(node.toxml(), 'lxml')

                            # CUBF is mandatory
                            cubf = extract_field_or_none(unit_xml, 'rl0105a', type=int)

                            # We skip all CUBFs other than those defined above
                            if cubf not in CUBFS_TO_KEEP:
                                continue

                            # First get the MAT18 to create the provincial ID
                            mat18 = get_mat18(unit_xml)
                            id = muni_code + mat18

                            # Check if the unit already exists before doing any more work
                            if EvalUnit.objects.filter(id=id).first():

                                if i % 5_000 == 0:
                                    current_offset = event_stream.stream.tell()
                                    if current_offset != last_offset:
                                        offset_delta = current_offset - last_offset
                                        progress_bar.update(offset_delta)
                                        last_offset = current_offset
                                continue
                            
                            # Start filling the unit values
                            unit_data = {}
                            unit_data['id'] = id
                            unit_data['cubf'] = cubf
                            unit_data['muni'] = MUNICIPALITIES[f'RL{muni_code}']
                            unit_data['muni_code'] = muni_code
                            unit_data['year'] = year_entered
                            unit_data['mat18'] = mat18
                            current_units.append(parse_unit_xml(unit_xml, unit_data))

                    # Print an update and commit latest writes
                    if len(current_units) % 1000 == 0 and len(current_units) > 0:
                        current_offset = event_stream.stream.tell()
                        if current_offset != last_offset:
                            offset_delta = current_offset - last_offset
                            progress_bar.update(offset_delta)
                            last_offset = current_offset
                        EvalUnit.objects.bulk_create(current_units)
                        worker_total_units += len(current_units)
                        current_units = []

                except KeyboardInterrupt:
                    progress_bar.close()
                    return worker_total_units

                except:
                    print(traceback.format_exc())
                    print(f"{xml_file} - around tag {i}")
                    print(unit_xml.prettify())
                    continue


            # End of current file
            current_offset = event_stream.stream.tell()
            if current_offset != last_offset:
                offset_delta = current_offset - last_offset
                last_offset = current_offset
                progress_bar.update(offset_delta)

            # Flush out the current file's units
            EvalUnit.objects.bulk_create(current_units)
            worker_total_units += len(current_units)

        # Catch any unexpected error and continue
        except SAXParseException:
            print(traceback.format_exc())
            print(f"{xml_file} - i: {i}, j: {j}\nevt: {evt} node: {node}")
            continue

        finally:
            event_stream.clear()

    progress_bar.close()
    return worker_total_units



def get_mat18(unit):
    # RL0104 - we'll use it to create the MAT18 and ID_PROVINC used in the GIS data
    # Do this first to check if the unit has already been entered and skip work
    rl0104 = unit.find('rl0104')
    return generate_mat18(rl0104)


def parse_unit_xml(unit_xml, unit_data: dict):
    """
    Main parsing method
    Parses the unit_xml and puts all relevant info into unit_data
    """

    # RL0101: Unit Identification Fields
    # Every unit must have at least RL0101Gx, so RL0101 will always be present
    # They made so that multiple RL0101x could be present, but in practice there's always a single one
    rl0101x = unit_xml.find('rl0101x')
    get_address_components_and_resolve(rl0101x, unit_data)

    # Keep the apt number separate from the street address
    # We can use this to merge MURBs that are disaggregated into indiviudal units
    get_apt_num_components(rl0101x, unit_data)

    # RL0102A 
    unit_data['arrond'] = extract_field_or_none(unit_xml, 'rl0102a')

    unit_data['file_num'] = extract_field_or_none(unit_xml, 'rl0106a')
    unit_data['nghbr_unit'] = extract_field_or_none(unit_xml, 'rl0107a')
    

    # RL0201 - Owner Info
    # These are all mandatory fields
    # Most of it is redacted but we can know if the owner is a physical or moral person
    rl0201 = unit_xml.find('rl0201')

    # There can be multiple signup dates to the assessment roll
    # Take only the latest one
    max_date = datetime.strptime('1500-01-01', '%Y-%m-%d')
    for rl0201x in rl0201.find_all('rl0201x'):
        
        rl0201gx_tmp = rl0201x.find('rl0201gx').text
        date_time = datetime.strptime(rl0201gx_tmp, '%Y-%m-%d')

        if date_time > max_date:
            owner_date = rl0201gx_tmp
            if rl0201x.find('rl0201hx').text == '1':
                owner_type = 'physical'
            else:
                owner_type = 'moral'

    unit_data['owner_date'] = owner_date
    unit_data['owner_type'] = owner_type

    # Resolve the owner status from an integer to human readable value
    unit_data['owner_status'] = extract_field_or_none(rl0201, 'rl0201u', type=str)
    if owner_status := unit_data['owner_status']:
        if owner_status in OWNER_STATUSES:
            unit_data['owner_status'] = OWNER_STATUSES[owner_status]
        else:
            print(f'\t\tWARNING: Unknown owner status {owner_status}')

    # RL030Xx - Unit Characteristics
    unit_data['lot_lin_dim'] = extract_field_or_none(unit_xml, 'rl0301a', type=float)
    unit_data['lot_area'] = extract_field_or_none(unit_xml, 'rl0302a', type=float)
    unit_data['max_floors'] = extract_field_or_none(unit_xml, 'rl0306a', type=int)
    unit_data['const_yr'] = extract_field_or_none(unit_xml, 'rl0307a', type=int)
    unit_data['const_yr_real'] = extract_field_or_none(unit_xml, 'rl0307b')
    unit_data['floor_area'] = extract_field_or_none(unit_xml, 'rl0308a', type=float)

    # Resolve physical link to human readable value
    unit_data['phys_link'] = extract_field_or_none(unit_xml, 'rl0309a', type=str)
    if phys_link := unit_data['phys_link']:
        if phys_link in PHYSICAL_LINKS:
            unit_data['phys_link'] = PHYSICAL_LINKS[phys_link]
        else:
            print(f'\t\tWARNING: Unknown physical link {phys_link}')

    # Resolve construction type to human readable value
    unit_data['const_type'] = extract_field_or_none(unit_xml, 'rl0310a', type=str)
    if const_type := unit_data['const_type']:
        if const_type in CONSTRUCTION_TYPES:
            unit_data['const_type'] = CONSTRUCTION_TYPES[const_type]
        else:
            print(f'\t\tWARNING: Unknown construction type {const_type}')

    unit_data['num_dwelling'] = extract_field_or_none(unit_xml, 'rl0311a', type=int)
    unit_data['num_rental'] = extract_field_or_none(unit_xml, 'rl0312a', type=int)
    unit_data['num_non_res'] = extract_field_or_none(unit_xml, 'rl0313a', type=int)
    # rl0314 - rl0315 are related to agricultural zones, we ignore them here

    # RL040XX - Value 
    unit_data['apprais_date'] = extract_field_or_none(unit_xml, 'rl0401a')
    unit_data['lot_value'] = extract_field_or_none(unit_xml, 'rl0402a', type=float)
    unit_data['building_value'] = extract_field_or_none(unit_xml, 'rl0403a', type=float)
    unit_data['value'] = extract_field_or_none(unit_xml, 'rl0404a', type=float)
    unit_data['prev_value'] = extract_field_or_none(unit_xml, 'rl0405a', type=float)

    return EvalUnit(**unit_data)


def extract_field_or_none(unit_xml, field_id, type=None):
    if field := unit_xml.find(field_id):
        field = field.text
        if type:
            return type(field)
        return field
    # else
    return None

def extract_field_or_empty_string(unit_xml, field_id):
    if field := unit_xml.find(field_id):
        return field.text
    return ''
            

def get_address_components_and_resolve(rl0101x, unit_data):
    """
    Add address subfields and fully resolved address to unit_data
    I opted not to include the unresolved way link, type and cardinal points
    as they were not very interesting by themselves, instead keeping
    a nicely formatted address and street name fields containing the info
    """
    address_components = []

    if num_adr_inf := rl0101x.find('rl0101ax'):
        unit_data['num_adr_inf'] = num_adr_inf.text
        address_components.append(num_adr_inf.text)
    else:
        unit_data['num_adr_inf'] = None
    
    if num_adr_inf_2 := rl0101x.find('rl0101bx'):
        unit_data['num_adr_inf_2'] = num_adr_inf_2.text
        address_components.append(num_adr_inf_2.text)
    else:
        unit_data['num_adr_inf_2'] = None

    if num_adr_sup := rl0101x.find('rl0101cx'):
        unit_data['num_adr_sup'] = num_adr_sup.text
        address_components.append('-')
        address_components.append(num_adr_sup.text)
    else:
        unit_data['num_adr_sup'] = None

    if num_adr_sup_2 := rl0101x.find('rl0101dx'):
        unit_data['num_adr_sup_2'] = num_adr_sup_2.text
        address_components.append(num_adr_sup_2.text)
    else:
        unit_data['num_adr_sup_2'] = None

    # Process the street name
    street_components = []
    if way_type := rl0101x.find('rl0101ex'):
        # Resolve the way type
        way_type = WAY_TYPES[way_type.text]
        address_components.append(way_type)
        street_components.append(way_type)

    if way_link := rl0101x.find('rl0101fx'):
        way_link = WAY_LINKS[way_link.text]
        address_components.append(way_link)
        street_components.append(way_link)

    if street_name := rl0101x.find('rl0101gx'):
        street_name = street_name.text
        address_components.append(street_name)
        street_components.append(street_name)

    if cardinal_pt := rl0101x.find('rl0101hx'):
        cardinal_pt = CARDINAL_POINTS[cardinal_pt.text]
        address_components.append(cardinal_pt)
        street_components.append(cardinal_pt)

    unit_data['street_name'] = " ".join(street_components).title()
    unit_data['address'] = " ".join(address_components).title()


def get_apt_num_components(rl0101x, unit_data):
    apt_num_components = []

    if apt_num_1 := rl0101x.find('rl0101ix'):
        unit_data['apt_num_1'] = apt_num_1.text
        apt_num_components.append(apt_num_1.text)
    else:
        unit_data['apt_num_1'] = None

    if apt_num_2 := rl0101x.find('rl0101jx'):
        unit_data['apt_num_2'] = apt_num_2.text
        apt_num_components.append(apt_num_2.text)
    else:
        unit_data['apt_num_2'] = None

    if apt_num_components:
        unit_data['apt_num'] = " ".join(apt_num_components)
    else:
        unit_data['apt_num'] = None


def generate_mat18(rl0104):
    mat18 = ''
    # rl0104a to c are guaranteed to be present
    mat18 += rl0104.find('rl0104a').text
    mat18 += rl0104.find('rl0104b').text
    mat18 += rl0104.find('rl0104c').text

    # These 3 are optional, if not present, pad with zeros
    if chiffre_auto_verif := rl0104.find('rl0104d'):
        mat18 += chiffre_auto_verif.text
    else:
        mat18 += '0'

    if num_bat := rl0104.find('rl0104e'):
        mat18 += num_bat.text
    else:
        mat18 += '000'

    if num_local := rl0104.find('rl0104f'):
        mat18 += num_local.text
    else:
        mat18 += '0000'

    return mat18

