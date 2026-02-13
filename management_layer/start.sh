#!/bin/bash
set -e

# Run database migrations (if any)
# python migrate_db.py  <-- Uncomment if you have a migration script like this

# Start the application
exec python main.py
