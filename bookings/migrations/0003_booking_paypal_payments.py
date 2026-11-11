from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('bookings', '0002_booking_nightly_rate_room_active_and_protect'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='payment_status',
            field=models.CharField(choices=[('Unpaid', 'Unpaid'), ('Paid', 'Paid')], default='Unpaid', max_length=10),
        ),
        migrations.AddField(
            model_name='booking',
            name='paypal_order_id',
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='booking',
            name='paypal_capture_id',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name='booking',
            name='paid_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
