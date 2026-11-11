import logging

from django.core.mail import send_mail
from django.db import transaction
from django.conf import settings

from .models import Booking


logger = logging.getLogger(__name__)


def room_is_available(room, check_in, check_out, exclude_booking_id=None):
    conflicts = Booking.objects.filter(
        room=room,
        status__in=['Pending', 'Confirmed'],
        check_in__lt=check_out,
        check_out__gt=check_in,
    )
    if exclude_booking_id:
        conflicts = conflicts.exclude(pk=exclude_booking_id)
    return not conflicts.exists()


def notify_booking_change(booking, event):
    if not booking.user.email:
        return

    subject_by_event = {
        'created': 'Booking request received',
        'updated': 'Booking updated',
        'paid': 'Payment received; booking awaiting confirmation',
        'confirmed': 'Booking confirmed',
        'cancelled': 'Booking cancelled',
    }
    subject = f"{subject_by_event[event]} — Hotel Booking"
    body = (
        f"Hello {booking.user.first_name or booking.user.username},\n\n"
        f"{subject_by_event[event]}.\n\n"
        f"Room: {booking.room.room_name}\n"
        f"Check-in: {booking.check_in:%B %d, %Y}\n"
        f"Check-out: {booking.check_out:%B %d, %Y}\n"
        f"Nights: {booking.nights}\n"
        f"Rate per night: ₱{booking.rate_per_night}\n"
        f"Room subtotal: ₱{booking.subtotal_price}\n"
        f"Booking total: ₱{booking.total_price}\n"
        f"Status: {booking.status}\n\n"
        f"Payment: {booking.payment_status}\n\n"
        "Thank you for booking with us."
    )

    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [booking.user.email])
    except Exception:
        logger.exception('Could not send booking notification for booking %s', booking.pk)


def schedule_booking_notification(booking, event):
    transaction.on_commit(lambda: notify_booking_change(booking, event))
