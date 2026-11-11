from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('bookings', '0003_booking_paypal_payments'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='tax_rate',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
    ]
