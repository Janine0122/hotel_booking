# Payments and email setup

The site defaults to PayPal Sandbox and PHP. Booking tax is currently 0%, as requested. PayPal checkout stays hidden until API credentials are set.

## PayPal Sandbox

1. Create a PayPal REST app in the PayPal Developer Dashboard and copy its sandbox client ID and secret. PayPal requires a Business account to test integrations outside the US.
2. Set these environment variables in the same terminal that starts Django:

   ```powershell
   $env:PAYPAL_CLIENT_ID = "your-sandbox-client-id"
   $env:PAYPAL_CLIENT_SECRET = "your-sandbox-client-secret"
   $env:PAYPAL_MODE = "sandbox"
   ```

3. Apply the database migrations and restart the Django server:

   ```powershell
   python manage.py migrate
   python manage.py runserver
   ```

4. Use a PayPal sandbox personal account to pay against the matching sandbox business app.

The merchant account must be set to accept PHP payments, or PayPal may hold a different-currency payment for manual approval.

For live checkout, use the live app credentials and set `PAYPAL_MODE` to `live`. Keep the secret only in server environment variables; the client ID is intended for the checkout page.

## Email delivery

Booking emails use Django's console backend by default. To send real email, configure an SMTP provider in the Django process environment:

```powershell
$env:EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
$env:EMAIL_HOST = "smtp.example.com"
$env:EMAIL_PORT = "587"
$env:EMAIL_HOST_USER = "your-smtp-user"
$env:EMAIL_HOST_PASSWORD = "your-smtp-password"
$env:EMAIL_USE_TLS = "true"
$env:EMAIL_USE_SSL = "false"
$env:DEFAULT_FROM_EMAIL = "Hotel Booking <bookings@example.com>"
```

The server sends a notice when a guest books, changes dates, cancels, or completes PayPal payment, and when an admin confirms or cancels a booking.
