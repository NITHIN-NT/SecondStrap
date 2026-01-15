from django import forms
from django.forms import inlineformset_factory
from  products.models import Product,ProductVariant,ProductImage,Size,Category
from coupon.models import Coupon,CouponType
from django.utils import timezone
from django.core.exceptions import ValidationError

class AdminLoginForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        max_length=254,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
class AdminForgotPasswordEmailForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class':'form-control'}))


class AdminVerifyOTPForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        min_length=6
    )

class AdminSetNewPassword(forms.Form):
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

class AdminProductAddForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'category', 'image',
            'description', 'is_featured', 'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'id': 'product_name', 'required': True}),
            'category': forms.Select(attrs={'id': 'category', 'required': True}),
            'image': forms.FileInput(attrs={'id': 'main_product_image', 'accept': 'image/*'}),
            'description': forms.Textarea(attrs={'id': 'description', 'rows': 6}),
            'is_featured': forms.CheckboxInput(attrs={'id': 'is_featured'}),
            'is_active': forms.CheckboxInput(attrs={'id': 'is_active'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['image'].required = False
        else:
            self.fields['image'].required = True


class VariantForm(forms.ModelForm):
    size = forms.ModelChoiceField(
        queryset=Size.objects.all().order_by('size'),
        widget=forms.Select(attrs={'class': 'variant-size', 'required': True})
    )

    class Meta:
        model = ProductVariant
        fields = ['size', 'base_price', 'offer_price', 'stock']
        widgets = {
            'base_price': forms.NumberInput(attrs={'class': 'variant-base-price', 'step': '0.01', 'min': '0', 'required': True}),
            'offer_price': forms.NumberInput(attrs={'class': 'variant-offer-price', 'step': '0.01', 'min': '0'}),
            'stock': forms.NumberInput(attrs={'class': 'variant-stock', 'min': '0', 'required': True}),
        }

class ImageForm(forms.ModelForm):
    image = forms.ImageField(
        widget=forms.FileInput(attrs={'class': 'gallery-image', 'accept': 'image/*'}),
        label="Image File",
        required=False
    )
    alt_text = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'gallery-alt-text', 'placeholder': 'Describe the image'}),
        required=False
    )

    # ADD THIS SECTION
    class Meta:
        model = ProductImage
        fields = ['image', 'alt_text']
        
    def clean(self):
        cleaned_data = super().clean()
        image = cleaned_data.get('image')
        alt_text = cleaned_data.get('alt_text')
        
        if cleaned_data.get('DELETE'):
            return cleaned_data
        
        if alt_text and not image:
            if not self.instance.pk or 'image' in self.changed_data:
                self.add_error('image', 'An image file is required if you provide alt text.')

        if image and not alt_text:
            if 'image' in self.changed_data or not self.instance.pk:
                self.add_error('alt_text', 'Please provide alt text for the new image.')

        return cleaned_data

# Formsets
VariantFormSet = inlineformset_factory(
    Product, ProductVariant,
    form=VariantForm,
    fields=['size', 'base_price', 'offer_price', 'stock'],
    extra=1,
    min_num=1,
    can_delete=True,
    can_delete_extra=True
)

ImageFormSet = inlineformset_factory(
    Product, ProductImage,
    form=ImageForm,
    fields=['image', 'alt_text'],
    extra=1,
    min_num=3,
    validate_min=True,
    can_delete=True,
    can_delete_extra=True
)

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if not name:
            raise forms.ValidationError("Please enter the Name !")

        query = Category.objects.filter(name__iexact=name)

        if self.instance and self.instance.pk:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise forms.ValidationError(f"A category with the name '{name}' already exists.")
        
        return name

    def clean_description(self):
        description = self.cleaned_data.get("description")

        if not description:
            raise forms.ValidationError('Please Enter a Proper Description !')

        if len(description) > 200:
            raise forms.ValidationError('Description needs to be shorter than 200 characters.')
        return description
    
class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        exclude = ['created_at', 'updated_at', 'times_used']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control','placeholder': 'e.g., SUMMER20'}),
            'name': forms.TextInput(attrs={'class': 'form-control','placeholder': 'e.g., Summer Sale 2024'}),
            'description': forms.Textarea(attrs={'class': 'form-control','placeholder': 'Internal notes about this coupon...'}),
            'coupon_type': forms.Select(attrs={'class': 'form-control'}),
            'coupon_amount': forms.NumberInput(attrs={'class': 'form-control','placeholder': '0.00',}),
            'coupon_percentage': forms.NumberInput(attrs={'class': 'form-control','placeholder': '0.00',}),
            'min_purchase_amount': forms.NumberInput(attrs={'class': 'form-control','placeholder': '0.00',}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control','type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'class': 'form-control','type': 'datetime-local'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'usage_limit': forms.NumberInput(attrs={'class': 'form-control','placeholder': 'Leave empty for unlimited'}),
            'one_time_per_user': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code:
            code = code.strip().upper()
            if len(code) < 5:
                raise ValidationError("Coupon code must be at least 3 characters long")
        return code

    def clean(self):
        cleaned_data = super().clean()
        
        coupon_type = cleaned_data.get('coupon_type')
        coupon_amount = cleaned_data.get('coupon_amount')
        coupon_percentage = cleaned_data.get('coupon_percentage')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        usage_limit = cleaned_data.get('usage_limit')
        
        if coupon_type == CouponType.FIXED_AMOUNT:
            if not coupon_amount or coupon_amount <= 0:
                raise ValidationError({'coupon_amount': 'Fixed amount is required and must be greater than 0 for fixed amount coupons'})
            cleaned_data['coupon_percentage'] = None
            
        elif coupon_type == CouponType.PERCENTAGE:
            if not coupon_percentage or coupon_percentage <= 0:
                raise ValidationError({'coupon_percentage': 'Percentage is required and must be greater than 0 for percentage coupons'})
            if coupon_percentage > 100:
                raise ValidationError({'coupon_percentage': 'Percentage cannot exceed 100%'})
            cleaned_data['coupon_amount'] = None
        
        if start_date and end_date:
            if end_date <= start_date:
                raise ValidationError({'end_date': 'End date must be after start date'})
        
        if usage_limit is not None and usage_limit < 1:
            raise ValidationError({'usage_limit': 'Usage limit must be at least 1 or leave blank for unlimited'})

        return cleaned_data