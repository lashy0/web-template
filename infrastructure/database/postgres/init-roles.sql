-- Login roles
CREATE ROLE web_app_migrator
    LOGIN PASSWORD :'migrator_password'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;

CREATE ROLE web_app_runtime
    LOGIN PASSWORD :'runtime_password'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;

-- Database access
REVOKE ALL ON DATABASE web_app FROM PUBLIC;
GRANT CONNECT ON DATABASE web_app TO web_app_migrator, web_app_runtime;

-- Application schema
REVOKE ALL ON SCHEMA public FROM PUBLIC;
ALTER SCHEMA public OWNER TO web_app_migrator;
GRANT USAGE ON SCHEMA public TO web_app_runtime;

-- Objects created before this bootstrap completes
GRANT SELECT, INSERT, UPDATE, DELETE
    ON ALL TABLES IN SCHEMA public TO web_app_runtime;
GRANT USAGE, SELECT, UPDATE
    ON ALL SEQUENCES IN SCHEMA public TO web_app_runtime;

-- Objects created later by migrations
ALTER DEFAULT PRIVILEGES FOR ROLE web_app_migrator IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO web_app_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE web_app_migrator IN SCHEMA public
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO web_app_runtime;
