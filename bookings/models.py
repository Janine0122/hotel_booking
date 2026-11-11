from decimal import Decimal, ROUND_HALF_UP

from django.db import models
from django.contrib.auth.models import User


class Room(models.Model):
    room_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    capacity = models.IntegerField()
    image_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.room_name


class Booking(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Cancelled', 'Cancelled'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('Unpaid', 'Unpaid'),
        ('Paid', 'Paid'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.PROTECT)
    check_in = models.DateField()
    check_out = models.DateField()
    nightly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    payment_status = models.CharField(max_length=10, choices=PAYMENT_STATUS_CHOICES, default='Unpaid')
    paypal_order_id = models.CharField(max_length=64, blank=True, null=True, unique=True)
    paypal_capture_id = models.CharField(max_length=64, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.room.room_name}"

    @property
    def nights(self):
        return max((self.check_out - self.check_in).days, 0)

    @property
    def rate_per_night(self):
        return self.nightly_rate if self.nightly_rate is not None else self.room.price

    @property
    def subtotal_price(self):
        return self.rate_per_night * self.nights

    @property
    def tax_amount(self):
        rate = self.tax_rate or Decimal('0.00')
        return (self.subtotal_price * rate / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @property
    def total_price(self):
        return self.subtotal_price + self.tax_amount
