from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Booking, Room
from .services import room_is_available


class Register_form(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class Booking_form(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['check_in', 'check_out']
        widgets = {
            'check_in': forms.DateInput(attrs={'type': 'date'}),
            'check_out': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, room=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.room = room

    def clean(self):
        data = super().clean()
        check_in = data.get('check_in')
        check_out = data.get('check_out')

        if check_in and check_in < timezone.localdate():
            raise forms.ValidationError("Check-in date cannot be in the past.")
        if check_in and check_out and check_out <= check_in:
            raise forms.ValidationError("Check-out must be after check-in.")
        room = self.room or getattr(self.instance, 'room', None)
        if room and check_in and check_out and check_out > check_in:
            if not room_is_available(room, check_in, check_out, self.instance.pk):
                raise forms.ValidationError("This room is not available for those dates. Please choose another stay.")
        return data


class Room_form(forms.ModelForm):
    class Meta:
        model = Room
        fields = ['room_name', 'description', 'price', 'capacity', 'image_url']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'image_url': forms.HiddenInput(),
        }
