# ReCONstruct building identification tool

The goal of this tool is to provide a convenient way for users to rate the retrofit potential of buildings.

We first geocode addresses, then provide a live streetview of them. A first version had users determine the facade materials of buildings, with a 1-5 certainty rating, and could add new materials and add a note about the building, containing additional information.

The latest version focuses on identifying pre-fabricated metal buildings. The set of conditions will then be extended in a future version to further refine the selection.  

![image](assets/screenshot1.JPG)

# Installation

## 0. Get a Google Maps API key

This project makes use of the google maps API. To run it locally, you will need to obtain an authorization key.
Ask us for one from ReCONstruct, or set up your own by following the instructions [here](https://developers.google.com/maps/documentation/javascript/cloud-setup). (You will need to input a credit card, but local development and testing should come out at less than $5-10).

Once you have a key, set the `GOOGLE_MAPS_API_KEY` variable to it in the file `config/settings.py`.

## 1. (Optional) Create a virtual environment for the project
Virtual environments (venv for short) hold all dependencies for your project, and allow avoiding package version conflicts at the system level.
Each project has its specific dependency package versions installed in its virtual environment. 
This comes at the cost of disk space to store potential duplicate packages, for porject who would use the same ones. 
```
python -m venv .venv        # Will create the virtual environment in the '.venv' folder
.venv\Scripts\activate      # On Windows
source .venv/bin/activate   # On Linux/Mac
```

## 2. Install dependencies
```
pip install -r requirements.txt
```

## 3. Create the database and fill it with data

### Step 1:

Download and install [PostgreSQL](https://www.postgresql.org/) and the [PostGIS extension](https://postgis.net/documentation/getting_started), used for geospatial work. This code may work with other SQL databases, but was only tested with Postgres.

Make sure `psql` and `shp2pgsql` are on your path. You should be able to use the `psql` command to connect to postgres like so:
```bash
psql -U postgres
```



### Step 2:

Create a PostgreSQL DB and user, and activate the postgis extension.
```sql
CREATE USER bitdbuser WITH PASSWORD 'password';
ALTER ROLE bitdbuser SET client_encoding TO 'utf8';
ALTER ROLE bitdbuser SET default_transaction_isolation TO 'read committed';
ALTER ROLE bitdbuser SET timezone TO 'UTC';
CREATE DATABASE bitdb OWNER bitdbuser LC_COLLATE 'en_US.UTF-8' LC_CTYPE 'en_US.UTF-8' TEMPLATE 'template0';
GRANT ALL PRIVILEGES ON DATABASE bitdb TO bitdbuser;
GRANT ALL ON SCHEMA public TO bitdbuser;
ALTER USER bitdbuser SUPERUSER; --- Needed to create the test database and add extensions
\c bitdb -- Connects to the DB
CREATE EXTENSION postgis; -- activate the PostGIS extension for geographic calculations
CREATE EXTENSION pg_trgm; -- activate the extension for fuzzy string matching
``` 

You can rename the DB and user as your wish, however you must place those values in your local .env file, filling in the following fields:
Django will user these credentials to access the DB.
```conf
# DB connections settings
POSTGRES_NAME=bitdb
POSTGRES_USER=bitdbuser
POSTGRES_PW=password
POSTGRES_HOST=localhost # DB is running locally
POSTGRES_PORT=5432 # default port number for postgres
``` 

### Step 3:
Run the Django migrations, this will create all tables for our application in the DB.
```bash
python manage.py migrate
```

### Step 4: Setting up the Database

The database setup pipelines consists of the following steps:
- Import and process the roll XML files. These contain all the evaluation units in Quebec.
- Import and process the roll SHP files which gives us the lat/lng coordinates for each evaluation unit.
- Import and process the lot SHP. This gives us the polygon for each lot.
- Aggregate individually listed condos into single entries representing their building.
- Import the HLM dataset and map it to evaluation units.

The entire process takes around 6.5 hours!

```bash
python manage.py setup_database
```


### Alternatively, import test database

TODO


## 5. Start the server

The final step is to run the development server. This will make the application run at `http://127.0.0.1:8000/`.
Note that every access to the "Classify" section of the app will incur a Google Maps Javascript API call for a dynamic streetview and will thus incur a cost ($0.014 USD).

```bash
python manage.py runserver
```

You can create an admin user directly through the django shell.
```bash
python manage.py shell
```
```python
>>> from buildings.models import *
>>> u = User.objects.create_user("you-username", password="your-password")
>>> u.is_superuser = True
>>> u.is_staff = True
>>> u.save()
```


<br>
