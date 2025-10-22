#!/bin/bash
# Database Setup Script for Subjugate Online

set -e

echo "=== Subjugate Online - Database Setup ==="

# Configuration
DB_NAME="subjugate_online"
DB_USER="subjugate"
DB_PASSWORD="subjugate123"
DB_HOST="localhost"
DB_PORT="5432"

echo "Creating PostgreSQL database and user..."

# Create database user
sudo -u postgres psql <<EOF
-- Create user if not exists
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$DB_USER') THEN
    CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';
  END IF;
END
\$\$;

-- Create database if not exists
SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF

echo "Database setup complete!"
echo ""
echo "Database Connection Info:"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo "  Connection String: postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
