-- Initialize PostgreSQL database for Community Alert System

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Set timezone
SET timezone = 'UTC';

-- Create database (if not exists)
SELECT 'CREATE DATABASE alert_system_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'alert_system_db');

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE alert_system_db TO alert_user;