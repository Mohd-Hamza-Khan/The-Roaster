# forms.py

from django import forms
from django.forms import modelformset_factory  # Add this import
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Availability

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500 transition duration-150 ease-in-out',
                'placeholder': 'Choose a username',
            }),
            # Meta widgets won't be applied to password1/password2 because they are defined
            # on the form (UserCreationForm). We'll update those in __init__ below.
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure username widget attrs (in case Meta didn't apply)
        self.fields['username'].widget.attrs.update({
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500 transition duration-150 ease-in-out',
            'placeholder': 'Choose a username',
        })
        # Password fields are defined by UserCreationForm, add attrs explicitly
        pwd_attrs_common = {
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500 transition duration-150 ease-in-out',
            'placeholder': 'Enter your password',
        }
        self.fields['password1'].widget.attrs.update(pwd_attrs_common)
        # password2 should have its own placeholder
        self.fields['password2'].widget.attrs.update({
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500 transition duration-150 ease-in-out',
            'placeholder': 'Confirm your password',
        })

class AvailabilityForm(forms.ModelForm):
    class Meta:
        model = Availability
        fields = ['day_of_week', 'start_time', 'end_time']
        widgets = {
            'day_of_week': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500'
            }),
            'start_time': forms.TimeInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500',
                'type': 'time'
            }),
            'end_time': forms.TimeInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500',
                'type': 'time'
            })
        }

# Create the formset factory for Availability
AvailabilityFormSet = modelformset_factory(
    Availability,
    form=AvailabilityForm,
    extra=0,
    max_num=10,
    can_delete=True
)
