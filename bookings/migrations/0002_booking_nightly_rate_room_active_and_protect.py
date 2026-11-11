import django.db.models.deletion
from django.db import migrations, models


def snapshot_existing_room_rates(apps, schema_editor):
    Booking = apps.get_model('bookings', 'Booking')
    for booking in Booking.objects.filter(nightly_rate__isnull=True).select_related('room').iterator():
        booking.nightly_rate = booking.room.price
        booking.save(update_fields=['nightly_rate'])


class Migration(migrations.Migration):
    dependencies = [
        ('bookings', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='room',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='booking',
            name='nightly_rate',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.RunPython(snapshot_existing_room_rates, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='booking',
            name='room',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='bookings.room'),
        ),
    ]
