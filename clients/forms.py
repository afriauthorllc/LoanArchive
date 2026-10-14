from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Client

class ClientEntryForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = [
            'passport_photo', 'first_name', 'last_name', 'nin', 
            'telephone_number', 'district', 'sub_county', 'parish', 'village', 'landmark'
        ]
        widgets = {
            'passport_photo': forms.ClearableFileInput(attrs={'class': 'form-input-file'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter first name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter last name'}),
            'nin': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., CM950... (14 characters)'}),
            'telephone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., +256770000000'}),
            'district': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'District'}),
            'sub_county': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Sub-county'}),
            'parish': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Parish'}),
            'village': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Village'}),
            'landmark': forms.Textarea(attrs={'class': 'form-control-text', 'rows': 2, 'placeholder': 'Nearby schools, buildings, LC1 references...'}),
        }

    def clean_nin(self):
        """Standardizes input formatting automatically before checking database entries."""
        nin = self.cleaned_data.get('nin')
        if nin:
            return nin.strip().upper()
        return nin
