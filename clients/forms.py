from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Client

class ClientEntryForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = [
            'passport_photo', 'full_name', 'nin', 
            'telephone_number', 'district', 'sub_county', 'parish', 'village', 'landmark'
        ]
        widgets = {
            'passport_photo': forms.ClearableFileInput(attrs={'class': 'form-input-file'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter full name e.g. John Doe'}),
            'nin': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., CM950... (14 characters)'}),
            'telephone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0770000000 or +256770000000'}),
            'district': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'District'}),
            'sub_county': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sub-county'}),
            'parish': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Parish'}),
            'village': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Village'}),
            'landmark': forms.Textarea(attrs={'class': 'form-control-text', 'rows': 2, 'placeholder': 'Nearby schools, buildings, LC1 references...'}),
        }

    def clean_nin(self):
        nin = self.cleaned_data.get('nin')
        if nin:
            return nin.strip().upper()
        return nin

    def clean_full_name(self):
        name = self.cleaned_data.get('full_name')
        if name:
            # Remove extra spaces and Title Case
            return ' '.join(name.strip().split()).title()
        return name

    def clean_telephone_number(self):
        # Let the model handle normalization, just strip spaces here
        phone = self.cleaned_data.get('telephone_number')
        if phone:
            return phone.strip()
        return phone