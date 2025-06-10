-- Create extensions needed for the application
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Set permissions for the default user
GRANT ALL PRIVILEGES ON DATABASE bitdb TO bitdbuser;
ALTER DATABASE bitdb OWNER TO bitdbuser;
GRANT ALL ON SCHEMA public TO bitdbuser;
