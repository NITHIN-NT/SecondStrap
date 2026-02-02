from django import forms
from .models import CustomUser
from django.core.validators import RegexValidator

class CustomUserRegisterForm(forms.Form):
    email = forms.EmailField(max_length=254,widget=forms.EmailInput(attrs={'class' : 'form-control'}))
    first_name = forms.CharField(max_length=150,required=True,widget=forms.TextInput(attrs={'class' : 'form-control'}), validators=[CustomUser.name_validator_regex])
    last_name = forms.CharField(max_length=150,required=True,widget=forms.TextInput(attrs={'class' : 'form-control'}), validators=[CustomUser.name_validator_regex])
    password = forms.CharField(required=True,
                                widget=forms.PasswordInput(attrs={'class': 'form-control'})
                               ,validators=[RegexValidator(regex='^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d).{8,}$',
                                                                         message='Password must contain at least one uppercase letter, one lowercase letter, one digit, and be at least 8 characters long.',
                                                                         code='invalid_password')])
    password_confirm = forms.CharField(required=True,
                                       widget=forms.PasswordInput(attrs={'class': 'form-control'})
                                       ,validators=[RegexValidator(regex='^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d).{8,}$',
                                                                         message='Password must contain at least one uppercase letter, one lowercase letter, one digit, and be at least 8 characters long.',
                                                                         code='invalid_password')])

    
    def clean_email(self):
        email = self.cleaned_data["email"]
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('Email Already Exists')
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "Passwords do not match.")

        return cleaned_data

class LoginForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        max_length=254,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

class ForgotPasswordEmailForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class':'form-control'}))

class VerifyOTPForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        min_length=6
    )

class SetNewPassword(forms.Form):
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password'
        })
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')

        if new_password1 and new_password2 and new_password1 != new_password2:
            raise forms.ValidationError("The two password fields didn't match.")
            
        return cleaned_data
