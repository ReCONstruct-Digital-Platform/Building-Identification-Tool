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

Download and Install PostgreSQL on your local machine: https://www.postgresql.org/download/

You should be able to use the `psql` command to login to postgres as the default user:
```bash
psql -U postgres
```

### Step 2:

Create a PostgreSQL DB and user for the application:
```sql
CREATE USER bitdbuser WITH PASSWORD 'password';
ALTER ROLE bitdbuser SET client_encoding TO 'utf8';
ALTER ROLE bitdbuser SET default_transaction_isolation TO 'read committed';
ALTER ROLE bitdbuser SET timezone TO 'UTC';
CREATE DATABASE bitdb OWNER bitdbuser LC_COLLATE 'en_US.UTF-8' LC_CTYPE 'en_US.UTF-8' TEMPLATE 'template0';
GRANT ALL PRIVILEGES ON DATABASE bitdb TO bitdbuser;
GRANT ALL ON SCHEMA public TO bitdbuser;
ALTER USER bitdbuser CREATEDB; --- Needed to create the test database
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
Make and run the Django migrations, this will create all tables for our application in the DB.
```bash
python manage.py makemigrations
python manage.py migrate
```

### Step 4:

Open a `psql` command line as either user `postgres` or `bitdbuser`, and connect to your new database.
```bash
psql -U bitdbuser
\c bitdb
```

Finally, import some test data from the CSV files in `./data/`. Make sure to give the path for your machine.

```sql
\copy buildings_evalunit FROM 'data/all_murbs.csv' DELIMITER ',' CSV HEADER;
\copy buildings_evalunit FROM 'data/all_potential_community_centers.csv' DELIMITER ',' CSV HEADER;
\copy buildings_hlmbuilding(id, eval_unit_id, project_id, organism, service_center, street_num, street_name, muni, postal_code, num_dwellings, num_floors, area_footprint, area_total, ivp, disrepair_state, interest_adjust_date, contract_end_date, category, building_id) FROM 'data/all_hlms.csv' DELIMITER ',' CSV HEADER;
```


## 5. Start the server

The final step is to run the development server. This will make the application run at `http://127.0.0.1:8000/`.
Note that every access to the "Classify" section of the app will incur a Google Maps Javascript API call for a dynamic streetview and will thus incur a cost ($0.014 USD).

```
python manage.py runserver
```

<br>


# Commands to generate the CSVs from the Roll DB

We have provided you with data in `./data` to fill up the BIT database. It was extracted from the Roll DB, which you can generate by following the instructions here: https://github.com/ReCONstruct-Digital-Platform/QC-Prop-Roll

```sql
--- Extract all MURBs from the Roll DB
\copy (SELECT r.id, lat, lng, muni, muni_code, arrond, address, num_adr_inf, num_adr_inf_2, num_adr_sup, num_adr_sup_2, street_name, apt_num, apt_num_1, apt_num_2, mat18, cubf, file_num, nghbr_unit, owner_date, owner_type, os.value as "owner_status", lot_lin_dim, lot_area, max_floors, const_yr, const_yr_real, floor_area, pl.value as "phys_link", ct.value as "const_type", num_dwelling, num_rental, num_non_res, apprais_date, lot_value, building_value, r.value, prev_value, associated, '2023-08-14' as "date_added" FROM roll r LEFT JOIN phys_link pl ON r.phys_link = pl.id LEFT JOIN const_type ct ON r.const_type = ct.id LEFT JOIN owner_status os ON r.owner_status = os.id WHERE cubf = 1000  AND num_dwelling >= 3) TO './data/all_murbs.csv' CSV HEADER;
```

```sql
-- Extract all potential community centers
\copy (SELECT r.id, lat, lng, muni, muni_code, arrond, address, num_adr_inf, num_adr_inf_2, num_adr_sup, num_adr_sup_2, street_name, apt_num, apt_num_1, apt_num_2, mat18, cubf, file_num, nghbr_unit, owner_date, owner_type, os.value as "owner_status", lot_lin_dim, lot_area, max_floors, const_yr, const_yr_real, floor_area, pl.value as "phys_link", ct.value as "const_type", num_dwelling, num_rental, num_non_res, apprais_date, lot_value, building_value, r.value, prev_value, associated, '2023-08-14' as "date_added" FROM roll r LEFT JOIN phys_link pl ON r.phys_link = pl.id LEFT JOIN const_type ct ON r.const_type = ct.id LEFT JOIN owner_status os ON r.owner_status = os.id WHERE cubf IN (6811, 6812, 6813, 6814, 6815, 6816, 7219, 7221, 7222, 7223, 7224, 7225, 7229, 7233, 7239, 7290, 7311, 7312, 7313, 7314, 7392, 7393, 7394, 7395, 7396, 7397, 7399, 7411, 7412, 7413, 7414, 7415, 7416, 7417, 7418, 7419, 7421, 7422, 7423, 7424, 7425, 7429, 7431, 7432, 7433, 7441, 7442, 7443, 7444, 7445, 7446, 7447, 7448, 7449, 7451, 7452, 7459, 7491, 7492, 7493, 7499, 7611)) TO './data/all_potential_community_centers.csv' CSV HEADER;
```

```sql
-- Extract all HLMs, with a condition that they link to one of the above extracted MURBs
\copy (SELECT hlm.id, eval_unit_id, project_id, organism, service_center, street_num, street_name, muni, postal_code, num_dwellings, num_floors, area_footprint, area_total, ivp, disrepair_state, interest_adjust_date, contract_end_date, category, building_id FROM hlm INNER JOIN (SELECT roll.id FROM roll WHERE cubf = 1000  AND num_dwelling >= 3) as murbs ON hlm.eval_unit_id = murbs.id) TO './data/all_hlms.csv' CSV HEADER;
```