# loans/forms.py
from django import forms
from .models import Loan

class LoanApplicationForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = ['client', 'branch', 'principal_amount', 'interest_rate', 'duration_months', 'collateral_details']
        widgets = {
            'client': forms.Select(attrs={'class':'input'}),
            'branch': forms.Select(attrs={'class':'input'}),
            'principal_amount': forms.NumberInput(attrs={'class':'input', 'placeholder':'500000'}),
            'interest_rate': forms.NumberInput(attrs={'class':'input', 'placeholder':'10.00'}),
            'duration_months': forms.NumberInput(attrs={'class':'input', 'placeholder':'1'}),
            'collateral_details': forms.Textarea(attrs={'class':'input', 'rows':3, 'placeholder':'e.g., Motorcycle Logbook UAX 123A, Land agreement in Mukono'}),
        }
        help_texts = {
            'principal_amount': 'Min UGX 1000',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # If officer has a branch, pre-select it
        if user and hasattr(user, 'branch') and user.branch:
            self.fields['branch'].initial = user.branch