# Deploying Hotel Booking to PythonAnywhere

## 1. Upload the project

Create a ZIP of the project source and upload it using the PythonAnywhere **Files** tab. Exclude the local `venv/`, `__pycache__/`, and `.pyc` files. Do not upload `db.sqlite3` if you do not want local account and booking data on the hosted site. If you leave it out, you will need to create an admin user and add rooms after deployment.

In a PythonAnywhere Bash console, unzip it into `/home/<your-pythonanywhere-username>/hotel_booking` and enter that folder (the one containing `manage.py`).

## 2. Create the web app and environment

In **Web > Add a new web app**, choose **Manual configuration** and Python **3.11**. In a Bash console:

```bash
cd ~/hotel_booking
mkvirtualenv --python=python3.11 hotel-booking-env
pip install -r requirements.txt
```

Set the virtualenv path in the Web tab to `/home/<your-pythonanywhere-username>/.virtualenvs/hotel-booking-env`.

## 3. Configure the PythonAnywhere WSGI file

Open the WSGI file linked in the Web tab. Set the project path, Django settings module, and production environment variables before `get_wsgi_application()`:

```python
import os
import sys

project_home = '/home/<your-pythonanywhere-username>/hotel_booking'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.environ['DJANGO_SETTINGS_MODULE'] = 'hotel_booking.settings'
os.environ['DJANGO_DEBUG'] = 'false'
os.environ['DJANGO_SECRET_KEY'] = 'paste-a-new-random-secret-here'
os.environ['DJANGO_ALLOWED_HOSTS'] = '<your-pythonanywhere-username>.pythonanywhere.com'
os.environ['DJANGO_CSRF_TRUSTED_ORIGINS'] = 'https://<your-pythonanywhere-username>.pythonanywhere.com'

# Optional: enable PayPal Sandbox checkout
os.environ['PAYPAL_MODE'] = 'sandbox'
os.environ['PAYPAL_CLIENT_ID'] = 'your-sandbox-client-id'
os.environ['PAYPAL_CLIENT_SECRET'] = 'your-sandbox-secret'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

Replace every `<...>` placeholder. Generate a new secret in the Bash console with:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Keep the WSGI file private; do not commit it or share the PayPal secret. The WSGI file on PythonAnywhere is separate from `hotel_booking/wsgi.py` in your project.

## 4. Initialize Django and static files

In the Bash console:

```bash
cd ~/hotel_booking
workon hotel-booking-env
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

In the Web tab's **Static files** section, map URL `/static/` to `/home/<your-pythonanywhere-username>/hotel_booking/staticfiles`.

If you chose not to upload the local database, sign in to `/admin/` and add your rooms. Then use the Web tab's **Reload** button and visit your `https://<your-pythonanywhere-username>.pythonanywhere.com` address.

## 5. Future updates

Upload or pull the changed source, install any new requirements, run migrations and `collectstatic` when needed, then click **Reload** on the Web tab. Check the error log linked on that tab if the site does not start.

## External API note

PythonAnywhere free accounts restrict server-side outbound internet access to an allowlist. This app's PayPal REST calls are made from Django on the server, so PayPal Sandbox may not work on a free account unless the relevant PayPal API domain is allowlisted. Paid accounts have unrestricted outbound access. Weather, holiday, map, and Cloudinary calls in this project are made by the visitor's browser instead.
