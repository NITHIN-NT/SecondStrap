from django import forms
from .models import Address

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            'full_name',
            'address_line_1',
            'address_line_2',
            'city',
            'state',
            'postal_code',
            'phone_number',
            'country',
            'is_default',
            'address_type',
        ]
        
    def clean(self):
        cleaned_data = super().clean()

        address_line_1 = cleaned_data.get('address_line_1')
        address_line_2 = cleaned_data.get('address_line_2')

        # Custom validation: at least one address line
        if not address_line_1 and not address_line_2:
            raise forms.ValidationError("Please enter at least one address line!")

        return cleaned_data