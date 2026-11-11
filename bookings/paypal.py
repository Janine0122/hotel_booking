import base64
import json
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

from django.conf import settings


class PayPalError(Exception):
    pass


def _api_base():
    return 'https://api-m.paypal.com' if settings.PAYPAL_MODE == 'live' else 'https://api-m.sandbox.paypal.com'


def _request(path, method='GET', payload=None, request_id=None):
    client_id = settings.PAYPAL_CLIENT_ID
    client_secret = settings.PAYPAL_CLIENT_SECRET
    if not client_id or not client_secret:
        raise PayPalError('PayPal is not configured. Add PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET.')

    credentials = base64.b64encode(f'{client_id}:{client_secret}'.encode()).decode()
    token_request = Request(
        f'{_api_base()}/v1/oauth2/token',
        data=urlencode({'grant_type': 'client_credentials'}).encode(),
        headers={
            'Authorization': f'Basic {credentials}',
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        method='POST',
    )
    try:
        with urlopen(token_request, timeout=20) as response:
            access_token = json.loads(response.read()).get('access_token')
        if not access_token:
            raise PayPalError('PayPal did not return an access token.')

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Prefer': 'return=representation',
        }
        if request_id:
            headers['PayPal-Request-Id'] = request_id
        body = json.dumps(payload).encode() if payload is not None else None
        api_request = Request(f'{_api_base()}{path}', data=body, headers=headers, method=method)
        with urlopen(api_request, timeout=30) as response:
            return json.loads(response.read())
    except HTTPError as error:
        details = error.read().decode(errors='replace')
        raise PayPalError(f'PayPal returned an error ({error.code}). {details[:500]}') from error
    except (URLError, TimeoutError) as error:
        raise PayPalError('Could not connect to PayPal. Please try again.') from error


def create_order(booking):
    value = f'{booking.total_price.quantize(Decimal("0.01")):.2f}'
    payload = {
        'intent': 'CAPTURE',
        'purchase_units': [{
            'reference_id': f'booking-{booking.pk}',
            'custom_id': str(booking.pk),
            'description': f'{booking.room.room_name} — {booking.nights} night(s)',
            'amount': {
                'currency_code': settings.PAYPAL_CURRENCY,
                'value': value,
            },
        }],
    }
    return _request('/v2/checkout/orders', 'POST', payload, request_id=str(uuid4()))


def capture_order(order_id):
    return _request(f'/v2/checkout/orders/{order_id}/capture', 'POST', {})


def get_order(order_id):
    return _request(f'/v2/checkout/orders/{order_id}')
