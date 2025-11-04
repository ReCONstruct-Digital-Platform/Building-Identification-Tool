import os
import csv
import json
import time
import locale
import logging
import traceback
import googlemaps
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import close_old_connections
from babel.numbers import parse_decimal
from buildings.models.newmodels import DatasetOnboardingJob, Dataset, Building
from buildings.utils import b2
from buildings.utils.utility import is_streetview_imagery_available

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Process dataset onboarding jobs and create buildings"

    def add_arguments(self, parser):
        parser.add_argument(
            "--job_id",
            type=int,
            help="ID of the specific DatasetOnboardingJob to process",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Process all pending DatasetOnboardingJobs",
        )

    def add_arguments(self, parser):
        parser.add_argument(
            "--job_id",
            type=int,
            help="ID of the specific DatasetOnboardingJob to process",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Process all pending DatasetOnboardingJobs",
        )
        parser.add_argument(
            "--continuous",
            action="store_true",
            default=True,
            help="Continuously poll for new pending jobs",
        )
        parser.add_argument(
            "--sleep",
            type=int,
            default=10,
            help="Sleep time in seconds between polling cycles (default: 10)",
        )

    def handle(self, *args, **options):
        job_id = options.get("job_id")
        process_all = options.get("all")
        continuous = options.get("continuous")
        sleep_time = options.get("sleep")

        if not job_id and not process_all and not continuous:
            self.stdout.write(
                self.style.ERROR(
                    "Please provide either a job_id, --all flag, or --continuous flag to process jobs"
                )
            )
            return

        try:
            if job_id:
                # Process a specific job
                try:
                    job = DatasetOnboardingJob.objects.get(id=job_id)
                    self.process_job(job)
                except DatasetOnboardingJob.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(
                            f"DatasetOnboardingJob with ID {job_id} not found"
                        )
                    )
            elif continuous:
                # Continuously poll for new pending jobs
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Starting continuous polling for pending jobs (sleep: {sleep_time}s)"
                    )
                )
                try:
                    while True:
                        # Get all pending jobs

                        pending_jobs = DatasetOnboardingJob.objects.filter(
                            status=DatasetOnboardingJob.Status.PENDING
                        )

                        if pending_jobs.exists():
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"Found {pending_jobs.count()} pending jobs"
                                )
                            )
                            for job in pending_jobs:
                                try:
                                    self.process_job(job)
                                except Exception as e:
                                    logger.error(
                                        f"Error processing job {job.id}: {str(e)}"
                                    )
                                    logger.error(traceback.format_exc())
                                    # Update job status to FAILED
                                    job.status = DatasetOnboardingJob.Status.FAILED
                                    job.save()
                                    close_old_connections()

                        else:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"No pending jobs found. Sleeping for {sleep_time} seconds..."
                                )
                            )

                        # Sleep before next polling cycle
                        time.sleep(sleep_time)
                except KeyboardInterrupt:
                    self.stdout.write(
                        self.style.SUCCESS("Received keyboard interrupt. Exiting...")
                    )
            else:
                # Process all pending jobs once and exit
                pending_jobs = DatasetOnboardingJob.objects.filter(
                    status=DatasetOnboardingJob.Status.PENDING
                )
                self.stdout.write(
                    self.style.SUCCESS(f"Found {pending_jobs.count()} pending jobs")
                )
                for job in pending_jobs:
                    try:
                        self.process_job(job)
                    except Exception as e:
                        logger.error(f"Error processing job {job.id}: {str(e)}")
                        logger.error(traceback.format_exc())
                        # Update job status to FAILED
                        job.status = DatasetOnboardingJob.Status.FAILED
                        job.save()
                        close_old_connections()
        except Exception as e:
            logger.error(f"Unexpected error in command: {str(e)}")
            logger.error(traceback.format_exc())

    def process_job(self, job):
        """
        Process a single DatasetOnboardingJob
        """
        self.stdout.write(
            self.style.SUCCESS(f"Processing job {job.id}: {job.name}")
        )

        try:
            # Update job status to PROCESSING
            job.status = DatasetOnboardingJob.Status.PROCESSING
            job.save()

            # Get the dataset associated with this job
            dataset = Dataset.objects.filter(name=job.name, created_by=job.created_by).first()

            if not dataset:
                self.stdout.write(
                    self.style.ERROR(f"Dataset for job {job.id} not found")
                )
                job.status = DatasetOnboardingJob.Status.FAILED
                job.save()
                return

            # Process the CSV file
            if not job.csv_file_location:
                self.stdout.write(
                    self.style.ERROR(f"CSV file for job {job.id} not found at {job.csv_file_location}")
                )
                job.status = DatasetOnboardingJob.Status.FAILED
                job.save()
                return

            # Read the CSV file and create buildings
            self.process_csv_file(job, dataset)

            # Update job status to COMPLETED
            job.status = DatasetOnboardingJob.Status.COMPLETED
            job.dataset = dataset
            job.save()

            self.stdout.write(
                self.style.SUCCESS(f"Successfully processed job {job.id}")
            )

        except Exception as e:
            error_msg = f"Error processing job {job.id}: {str(e)}"
            self.stdout.write(self.style.ERROR(error_msg))
            logger.error(error_msg)
            logger.error(traceback.format_exc())

            # Update job status to FAILED
            job.status = DatasetOnboardingJob.Status.FAILED
            job.save()

            # Reset database connection
            close_old_connections()

    def clean_csv_lines(self, lines):
        """
        Clean CSV lines by removing BOM and empty lines
        """
        cleaned_lines = []
        for line in lines:
            if line.startswith("\ufeff"):
                line = line.replace("\ufeff", "")

            if line.replace(",", "").strip():
                cleaned_lines.append(line)

        return cleaned_lines

    def process_csv_file(self, job, dataset):
        """
        Process the CSV file and create buildings
        """
        self.stdout.write(f"Processing CSV file: {job.csv_file_location}")

        # Get column mapping from job
        column_mapping = job.column_mapping

        # Check if we need to geocode addresses
        needs_geocoding = job.has_coordinates is False

        # Initialize Google Maps client if we need geocoding
        gmaps = None
        if needs_geocoding:
            if not hasattr(settings, 'GOOGLE_MAPS_API_KEY') or not settings.GOOGLE_MAPS_API_KEY:
                self.stdout.write(
                    self.style.ERROR("Google Maps API key not found in settings. Geocoding will not be available.")
                )
            else:
                gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)

        # Read CSV file
        buildings_to_create = []
        geocoding_failures = 0

        # Read CSV file from S3 using location
        b2_client = b2.get_client()

        csvfile = b2_client.get_object(
            Bucket=settings.B2_BUCKET_IMAGES, Key=job.csv_file_location
        )["Body"]

        if not csvfile:
            self.stdout.write(
                self.style.ERROR(
                    f"Could not read CSV file from {job.csv_file_location}"
                )
            )
            raise Exception(f"Could not read CSV file from {job.csv_file_location}")

        # Convert bytes to string and split by lines
        lines = csvfile.read().decode("utf-8").splitlines()
        cleaned_lines = self.clean_csv_lines(lines)

        reader = csv.DictReader(cleaned_lines)

        for row_num, row in enumerate(reader, 1):
            try:
                if row_num == 1:
                    # Remove BOM if present
                    row = {k.lstrip("\ufeff"): v for k, v in row.items()}
                    self.stdout.write(f"CSV Columns: {list(row.keys())}")

                # Create building object
                building_data = self.map_csv_row_to_building(
                    row, column_mapping, dataset.schema
                )

                # Add dataset reference
                building_data['dataset'] = dataset

                # If we need to geocode and have a Google Maps client
                if needs_geocoding and gmaps:
                    geocoded = self.geocode_building(building_data, gmaps)
                    if not geocoded:
                        # Store geocoding error in the dedicated field
                        building_data['geocoding_error'] = "Could not geocode address"
                        geocoding_failures += 1

                # If we have coordinates, create a Point object
                if 'lat' in building_data and 'lng' in building_data:
                    lat = building_data.get('lat')
                    lng = building_data.get('lng')
                    if lat and lng:
                        try:
                            lat = float(lat)
                            lng = float(lng)
                            building_data['lat'] = lat
                            building_data['lng'] = lng
                            building_data['point'] = Point(lng, lat)
                        except (ValueError, TypeError):
                            self.stdout.write(
                                self.style.WARNING(f"Invalid coordinates in row {row_num}: lat={lat}, lng={lng}")
                            )
                            building_data['geocoding_error'] = "Invalid coordinates"

                # Check if streetview is available at the location
                if 'point' in building_data:
                    streetview_available = is_streetview_imagery_available(
                        building_data['lat'],
                        building_data['lng'],
                        radius=50
                    )
                    building_data['has_streetview'] = streetview_available

                # Create Building object
                building = Building(**building_data)
                buildings_to_create.append(building)

                # Process in batches of 1000
                if len(buildings_to_create) >= 1000:
                    Building.objects.bulk_create(buildings_to_create)
                    buildings_to_create = []

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error processing row {row_num}: {str(e)}")
                )

        # Create any remaining buildings
        if buildings_to_create:
            Building.objects.bulk_create(buildings_to_create)

        if geocoding_failures > 0:
            self.stdout.write(
                self.style.WARNING(f"Failed to geocode {geocoding_failures} buildings")
            )

        self.stdout.write(
            self.style.SUCCESS(f"Successfully processed CSV file")
        )

    def geocode_building(self, building_data, gmaps):
        """
        Geocode a building using Google Maps API
        Returns True if geocoding was successful, False otherwise
        """
        # Construct the address query
        address_components = []

        # Add street number and name if available
        if 'street_num' in building_data and building_data['street_num']:
            address_components.append(str(building_data['street_num']))

        if 'street_name' in building_data and building_data['street_name']:
            address_components.append(building_data['street_name'])
        elif 'address' in building_data and building_data['address']:
            # If we have a full address but no street name, use the full address
            address_components = [building_data['address']]

        # Add municipality if available
        if 'muni' in building_data and building_data['muni']:
            address_components.append(building_data['muni'])

        # Add province if available
        if 'admin_area_level_1' in building_data and building_data['admin_area_level_1']:
            address_components.append(building_data['admin_area_level_1'])
        else:
            # Default to Quebec for Canadian addresses
            address_components.append('QC')

        # Add postal code if available
        if 'postal_code' in building_data and building_data['postal_code']:
            address_components.append(building_data['postal_code'])

        # Join all components into a single query string
        gmaps_query = ' '.join(address_components)

        # If we don't have enough address information, return False
        if not gmaps_query or len(gmaps_query.strip()) < 5:
            return False

        try:
            # Call Google Maps geocoding API
            geocode_result = gmaps.geocode(gmaps_query)

            if not geocode_result:
                return False

            geocode_result = geocode_result[0]

            # Check if we have a good result
            if 'geometry' in geocode_result and 'location' in geocode_result['geometry']:
                # Extract coordinates
                building_data['lat'] = geocode_result['geometry']['location']['lat']
                building_data['lng'] = geocode_result['geometry']['location']['lng']

                # Update address components if available
                for component in geocode_result['address_components']:
                    if 'street_number' in component['types']:
                        building_data['street_num'] = component['long_name']

                    if 'route' in component['types']:
                        building_data['street_name'] = component['long_name']

                # Update full address
                if 'street_num' in building_data and 'street_name' in building_data:
                    building_data['address'] = f"{building_data['street_num']} {building_data['street_name']}"

                return True

            return False
        except Exception as e:
            error_msg = f"Error geocoding address: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return False

    def _find_in_schema(self, field_name, schema: list):
        """
        Find a field in the dataset schema by name
        """
        for field in schema:
            if field.get("field") == field_name:
                return field
        return None

    def map_csv_row_to_building(self, row, column_mapping, schema: list):
        """
        Map a CSV row to a Building object using the column mapping
        """
        building_data = {}
        attrs_data = {}

        for field, column in column_mapping.items():
            schema_field = self._find_in_schema(field, schema)
            if not schema_field:
                self.stdout.write(
                    self.style.WARNING(
                        f"Field '{field}' in column '{column}' not found in dataset schema"
                    )
                )
                continue

            field_type = schema_field.get("type")

            if column in row:
                if field.startswith('attrs__'):
                    # This is a dynamic attribute
                    attr_name = field.replace('attrs__', '')
                    attrs_data[attr_name] = self.coerce_data_to_type(
                        row[column], field_type
                    )
                else:
                    # This is a standard field
                    building_data[field] = self.coerce_data_to_type(
                        row[column], field_type
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(f"Column '{column}' not found in CSV row: {row}")
                )

        # Add attrs data if we have any
        if attrs_data:
            building_data['attrs'] = attrs_data

        return building_data

    def coerce_data_to_type(self, value, data_type):
        """
        Coerce a string value to the specified data type
        """

        try:
            if data_type == "string":
                return str(value)
            elif data_type == "double":
                try:
                    val = float(value)
                except:
                    traceback.print_exc()
                try:
                    # Try parsing with fr locale for comma decimal separator
                    val = parse_decimal(value, locale="fr_CA")
                    val = float(val)
                except:
                    traceback.print_exc()
                return val

            elif data_type == "integer":
                return int(value)
            elif data_type == "boolean":
                return value.lower() in ("true", "1", "yes")
            elif data_type == "date":
                return value  # Date parsing can be implemented as needed
            else:
                return value
        except Exception as e:
            logger.error(
                f"Error coercing value '{value}' to type '{data_type}': {str(e)}"
            )
            traceback.print_exc()
            return None
