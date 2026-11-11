import json
import logging
from decimal import Decimal

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.db import transaction
from django.http import JsonResponse
from django.utils.dateparse import parse_date
from django.utils import timezone
from .models import Room, Booking
from .forms import Booking_form, Register_form, Room_form
from .services import room_is_available, schedule_booking_notification
from .paypal import PayPalError, capture_order as paypal_capture_order
from .paypal import create_order as paypal_create_order, get_order as paypal_get_order


logger = logging.getLogger(__name__)


def home_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard' if request.user.is_staff else 'guest_dashboard')
    return render(request, 'home.html')


def room_list_view(request):
    return render(request, 'rooms.html', {'rooms': Room.objects.filter(is_active=True)})


@login_required
@require_POST
def create_paypal_order_view(request):
    try:
        payload = json.loads(request.body or '{}')
        booking_id = int(payload.get('booking_id'))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({'error': 'Invalid booking.'}, status=400)

    try:
        with transaction.atomic():
            booking = get_object_or_404(
                Booking.objects.select_for_update(), pk=booking_id, user=request.user
            )
            if booking.payment_status == 'Paid':
                return JsonResponse({'error': 'This booking has already been paid.'}, status=409)
            if booking.status not in ['Pending', 'Confirmed']:
                return JsonResponse({'error': 'This booking cannot be paid.'}, status=409)
            if booking.paypal_order_id:
                return JsonResponse({'orderId': booking.paypal_order_id})
            if not room_is_available(booking.room, booking.check_in, booking.check_out, booking.pk):
                return JsonResponse({'error': 'This room is no longer available for those dates.'}, status=409)

            paypal_order = paypal_create_order(booking)
            if paypal_order.get('status') != 'CREATED' or not paypal_order.get('id'):
                return JsonResponse({'error': 'PayPal could not create the checkout order.'}, status=502)
            booking.paypal_order_id = paypal_order['id']
            booking.save(update_fields=['paypal_order_id'])
            return JsonResponse({'orderId': booking.paypal_order_id})
    except PayPalError as error:
        logger.warning('PayPal order creation failed for booking %s: %s', booking_id, error)
        status = 503 if not settings.PAYPAL_CLIENT_ID or not settings.PAYPAL_CLIENT_SECRET else 502
        message = 'PayPal is not configured yet.' if status == 503 else 'PayPal checkout could not start. Please try again.'
        return JsonResponse({'error': message}, status=status)


@login_required
@require_POST
def capture_paypal_order_view(request):
    try:
        payload = json.loads(request.body or '{}')
        booking_id = int(payload.get('booking_id'))
        order_id = str(payload.get('order_id', ''))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({'error': 'Invalid payment information.'}, status=400)

    if not order_id:
        return JsonResponse({'error': 'Missing PayPal order ID.'}, status=400)

    try:
        with transaction.atomic():
            booking = get_object_or_404(
                Booking.objects.select_for_update(), pk=booking_id, user=request.user
            )
            if booking.payment_status == 'Paid':
                return JsonResponse({'paid': True, 'message': 'This booking is already paid.'})
            if booking.paypal_order_id != order_id:
                return JsonResponse({'error': 'This PayPal order does not belong to this booking.'}, status=403)
            if booking.status not in ['Pending', 'Confirmed']:
                return JsonResponse({'error': 'This booking can no longer be paid.'}, status=409)
            if not room_is_available(booking.room, booking.check_in, booking.check_out, booking.pk):
                return JsonResponse({'error': 'This room is no longer available for those dates.'}, status=409)

            order = paypal_get_order(order_id)
            purchase_units = order.get('purchase_units') or []
            if not purchase_units:
                return JsonResponse({'error': 'PayPal returned an incomplete order.'}, status=502)
            purchase = purchase_units[0]
            expected_total = f'{booking.total_price.quantize(Decimal("0.01")):.2f}'
            amount = purchase.get('amount') or {}
            if (order.get('status') not in ['APPROVED', 'COMPLETED']
                    or amount.get('currency_code') != settings.PAYPAL_CURRENCY
                    or amount.get('value') != expected_total
                    or purchase.get('custom_id') != str(booking.pk)):
                return JsonResponse({'error': 'PayPal order details did not match this booking.'}, status=409)

            if order.get('status') == 'COMPLETED':
                captured_order = order
            else:
                captured_order = paypal_capture_order(order_id)

            capture_list = (captured_order.get('purchase_units') or [{}])[0].get('payments', {}).get('captures', [])
            capture = capture_list[0] if capture_list else {}
            capture_amount = capture.get('amount') or {}
            if (captured_order.get('status') != 'COMPLETED'
                    or capture.get('status') != 'COMPLETED'
                    or capture_amount.get('currency_code') != settings.PAYPAL_CURRENCY
                    or capture_amount.get('value') != expected_total):
                return JsonResponse({'error': 'PayPal has not completed the full payment.'}, status=402)

            booking.payment_status = 'Paid'
            booking.paypal_capture_id = capture.get('id', '')
            booking.paid_at = timezone.now()
            booking.save(update_fields=['payment_status', 'paypal_capture_id', 'paid_at'])
            schedule_booking_notification(booking, 'paid')
        return JsonResponse({'paid': True, 'message': 'Payment complete.'})
    except PayPalError as error:
        logger.warning('PayPal capture failed for booking %s: %s', booking_id, error)
        return JsonResponse({'error': 'PayPal could not complete this payment. Please try again.'}, status=502)


@login_required
@require_POST
def cancel_paypal_order_view(request):
    try:
        payload = json.loads(request.body or '{}')
        booking_id = int(payload.get('booking_id'))
        order_id = str(payload.get('order_id', ''))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({'error': 'Invalid payment information.'}, status=400)

    with transaction.atomic():
        booking = get_object_or_404(
            Booking.objects.select_for_update(), pk=booking_id, user=request.user
        )
        if booking.payment_status == 'Paid':
            return JsonResponse({'error': 'This booking has already been paid.'}, status=409)
        if not order_id or booking.paypal_order_id == order_id:
            booking.paypal_order_id = None
            booking.save(update_fields=['paypal_order_id'])
    return JsonResponse({'cancelled': True})


def register_view(request):
    if request.method == 'POST':
        form = Register_form(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = Register_form()
    return render(request, 'register_form.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'login_form.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def book_room_view(request, room_id):
    room = get_object_or_404(Room, id=room_id, is_active=True)
    if request.method == 'POST':
        with transaction.atomic():
            room = get_object_or_404(Room.objects.select_for_update(), id=room_id, is_active=True)
            form = Booking_form(request.POST, room=room)
            if form.is_valid():
                booking = form.save(commit=False)
                booking.user = request.user
                booking.room = room
                booking.nightly_rate = room.price
                booking.tax_rate = settings.BOOKING_TAX_RATE
                booking.save()
                schedule_booking_notification(booking, 'created')
        if form.is_valid():
            return redirect('my_bookings')
    else:
        form = Booking_form(initial={
            'check_in': request.GET.get('check_in'),
            'check_out': request.GET.get('check_out'),
        }, room=room)
    return render(request, 'book_room.html', {
        'form': form,
        'room': room,
        'tax_rate': settings.BOOKING_TAX_RATE,
        'paypal_client_id': settings.PAYPAL_CLIENT_ID,
    })


def check_room_availability_view(request, room_id):
    room = get_object_or_404(Room, id=room_id, is_active=True)
    try:
        check_in = parse_date(request.GET.get('check_in', ''))
        check_out = parse_date(request.GET.get('check_out', ''))
    except (TypeError, ValueError):
        return JsonResponse({'valid': False, 'message': 'Enter valid check-in and check-out dates.'}, status=400)
    if not check_in or not check_out:
        return JsonResponse({'valid': False, 'message': 'Choose both check-in and check-out dates.'}, status=400)
    if check_in < timezone.localdate():
        return JsonResponse({'valid': False, 'message': 'Check-in cannot be in the past.'}, status=400)
    if check_out <= check_in:
        return JsonResponse({'valid': False, 'message': 'Check-out must be after check-in.'}, status=400)
    available = room_is_available(room, check_in, check_out)
    return JsonResponse({
        'valid': True,
        'available': available,
        'message': 'This room is available for those dates.' if available else 'This room is already booked for some of those dates. Choose different dates.',
    })


@login_required
def my_bookings_view(request):
    # Admin sees all bookings, customers see only their own
    if request.user.is_staff:
        bookings = Booking.objects.all().order_by('-created_at')
    else:
        bookings = Booking.objects.filter(user=request.user).order_by('-created_at')

    return render(request, 'my_bookings.html', {
        'bookings': bookings,
        'paypal_client_id': settings.PAYPAL_CLIENT_ID,
        'paypal_mode': settings.PAYPAL_MODE,
        'today': timezone.localdate(),
    })


@login_required
def guest_dashboard_view(request):
    if request.user.is_staff:
        return redirect('dashboard')

    bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
    today = timezone.localdate()
    upcoming_bookings = bookings.filter(check_in__gte=today).exclude(status='Cancelled')
    return render(request, 'guest_dashboard.html', {
        'total_bookings': bookings.count(),
        'upcoming_count': upcoming_bookings.count(),
        'pending_count': bookings.filter(status='Pending').count(),
        'next_booking': upcoming_bookings.order_by('check_in').first(),
    })


@login_required
def edit_booking_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if booking.status != 'Pending':
        return redirect('my_bookings')

    if request.method == 'POST':
        form = Booking_form(request.POST, instance=booking, room=booking.room)
        if form.is_valid():
            booking = form.save()
            if booking.payment_status != 'Paid':
                booking.paypal_order_id = None
                booking.save(update_fields=['paypal_order_id'])
            schedule_booking_notification(booking, 'updated')
            return redirect('my_bookings')
    else:
        form = Booking_form(instance=booking, room=booking.room)
    return render(request, 'edit_booking.html', {'form': form, 'booking': booking})


@login_required
def cancel_booking_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    can_cancel = (
        booking.status in ['Pending', 'Confirmed']
        and booking.payment_status != 'Paid'
        and booking.check_in >= timezone.localdate()
    )
    if request.method == 'POST' and can_cancel:
        booking.status = 'Cancelled'
        booking.save()
        schedule_booking_notification(booking, 'cancelled')
    return redirect('my_bookings')


def is_admin(user):
    return user.is_staff


@user_passes_test(is_admin)
def dashboard_view(request):
    bookings = Booking.objects.all().order_by('-created_at')
    today = timezone.localdate()

    context = {
        'bookings': bookings,
        'total_bookings': bookings.count(),
        'pending_count': bookings.filter(status='Pending').count(),
        'today_checkins': bookings.filter(check_in=today).count(),
        'total_rooms': Room.objects.filter(is_active=True).count(),
    }
    return render(request, 'dashboard.html', context)


@user_passes_test(is_admin)
def update_status_view(request, booking_id, new_status):
    booking = get_object_or_404(Booking, id=booking_id)

    if request.method == 'POST' and new_status in ['Confirmed', 'Cancelled']:
        if new_status == 'Confirmed' and booking.payment_status != 'Paid':
            return redirect(request.META.get('HTTP_REFERER', 'dashboard'))
        if booking.payment_status == 'Paid' and new_status == 'Cancelled':
            return redirect(request.META.get('HTTP_REFERER', 'dashboard'))
        if (new_status == 'Confirmed'
                and not room_is_available(booking.room, booking.check_in, booking.check_out, booking.pk)):
            return redirect(request.META.get('HTTP_REFERER', 'dashboard'))
        changed = booking.status != new_status
        booking.status = new_status
        booking.save(update_fields=['status'])
        if changed:
            schedule_booking_notification(booking, 'confirmed' if new_status == 'Confirmed' else 'cancelled')

    # Go back to the page the admin came from
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))


@user_passes_test(is_admin)
def manage_rooms_view(request):
    rooms = Room.objects.all().order_by('-is_active', 'id')
    return render(request, 'manage_rooms.html', {'rooms': rooms})


@user_passes_test(is_admin)
def add_room_view(request):
    if request.method == 'POST':
        form = Room_form(request.POST)
        if form.is_valid():
            form.save()
            return redirect('manage_rooms')
    else:
        form = Room_form()
    return render(request, 'room_form.html', {'form': form, 'title': 'Add Room'})


@user_passes_test(is_admin)
def edit_room_view(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    if request.method == 'POST':
        form = Room_form(request.POST, instance=room)
        if form.is_valid():
            form.save()
            return redirect('manage_rooms')
    else:
        form = Room_form(instance=room)
    return render(request, 'room_form.html', {'form': form, 'title': 'Edit Room'})


@user_passes_test(is_admin)
def toggle_room_active_view(request, room_id):
    room = get_object_or_404(Room, id=room_id)
    if request.method == 'POST':
        room.is_active = not room.is_active
        room.save(update_fields=['is_active'])
    return redirect('manage_rooms')
