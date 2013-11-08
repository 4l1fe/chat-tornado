from django import forms
from .models import CustomUser


class SelectRooms(forms.ModelForm):

    class Meta:
        model = CustomUser
        fields = ('room',)