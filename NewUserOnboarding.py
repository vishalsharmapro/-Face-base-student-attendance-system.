import sqlite3
from django.contrib.auth.hashers import make_password
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project101.settings')

# Connect to the SQLite3 database
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()

# Define the SQL query to insert a new record
insert_query = """
INSERT INTO auth_user 
(id, password, last_login, is_superuser, username, last_name, email, is_staff, is_active, date_joined, first_name)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

# Generate a hashed password using Django's make_password
password = 'vishal1'
hashed_password = make_password(password)

# Define the new record data
new_record = (
    9,  # id
    hashed_password,  # password
    '2025-03-08 20:30:00.000000',  # last_login
    1,  # is_superuser
    'vishal1',  # username
    'Vishal',  # last_name
    'vishal@example.com',  # email
    1,  # is_staff
    1,  # is_active
    '2025-03-08 20:16:00.000000',  # date_joined
    'Vishal'  # first_name
)

# Execute the query with the new record data
cursor.execute(insert_query, new_record)

# Commit the transaction
conn.commit()

# Close the connection
conn.close()
