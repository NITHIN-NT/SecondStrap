from django import forms
from .models import Address
from django.core.validators import RegexValidator
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
    

class ChangePasswordForm(forms.Form):
    new_password = forms.CharField(required=True,
                                widget=forms.PasswordInput(attrs={'class': 'form-control'})
                               ,validators=[RegexValidator(regex='^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d).{8,}$',
                                                                         message='Password must contain at least one uppercase letter, one lowercase letter, one digit, and be at least 8 characters long.',
                                                                         code='invalid_password')])
    confirm_password = forms.CharField(required=True,
                                       widget=forms.PasswordInput(attrs={'class': 'form-control'})
                                       ,validators=[RegexValidator(regex='^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d).{8,}$',
                                                                         message='Password must contain at least one uppercase letter, one lowercase letter, one digit, and be at least 8 characters long.',
                                                                         code='invalid_password')])
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('new_password')
        password_confirm = cleaned_data.get('confirm_password')

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "Passwords do not match.")

        return cleaned_data

