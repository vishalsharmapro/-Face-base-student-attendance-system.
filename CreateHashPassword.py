from django.contrib.auth.hashers import make_password
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project101.settings')
def create_hashed_password(password):
    """
    Create a hashed password using Django's make_password function.
    """
    hashed_password = make_password(password)
    return hashed_password

# Example usage
password = 'vishal'
hashed_password = create_hashed_password(password)
print(f"Hashed password: {hashed_password}")
