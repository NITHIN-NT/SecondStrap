from django import forms
from django.forms import inlineformset_factory
from  products.models import Product,ProductVariant,ProductImage,Size,Category

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
            'name',  'category', 'base_price', 'image', 'offer_price',
            'description', 'is_featured', 'is_selective',
            'is_most_demanded', 'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'id': 'product_name', 'required': True}),
            # 'slug': forms.TextInput(attrs={'id': 'product_slug', 'readonly': 'readonly'}),
            'category': forms.Select(attrs={'id': 'category', 'required': True}),
            'image': forms.FileInput(attrs={'id': 'main_product_image', 'accept': 'image/*'}),
            'base_price': forms.NumberInput(attrs={'id': 'base_price', 'step': '0.01', 'required': True}),
            'offer_price': forms.NumberInput(attrs={'id': 'offer_price', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'id': 'description', 'rows': 6}),
            'is_featured': forms.CheckboxInput(attrs={'id': 'is_featured'}),
            'is_selective': forms.CheckboxInput(attrs={'id': 'is_selective'}),
            'is_most_demanded': forms.CheckboxInput(attrs={'id': 'is_most_demanded'}),
            'is_active': forms.CheckboxInput(attrs={'id': 'is_active'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['offer_price'].required = False
        if self.instance and self.instance.pk:
            self.fields['image'].required = False
        else:
            self.fields['image'].required = True

    def clean(self):
        cleaned_data = super().clean()
        base = cleaned_data.get('base_price')
        offer = cleaned_data.get('offer_price')
        if offer and base and offer >= base:
            self.add_error('offer_price', "Offer price must be less than base price.")
        return cleaned_data


class VariantForm(forms.ModelForm):
    size = forms.ModelChoiceField(
        queryset=Size.objects.all().order_by('size'),
        widget=forms.Select(attrs={'class': 'variant-size', 'required': True})
    )

    class Meta:
        model = ProductVariant
        fields = ['size', 'stock']
        widgets = {
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

    class Meta:
        model = ProductImage
        fields = ['image', 'alt_text']

    def clean(self):
        cleaned_data = super().clean()
        image = cleaned_data.get('image')
        alt_text = cleaned_data.get('alt_text')
        if cleaned_data.get('DELETE'):
            return cleaned_data
        
        if image and not alt_text:
            if 'image' in self.changed_data:
                self.add_error('alt_text', 'Please provide alt text for the new image.')

        return cleaned_data


# Formsets
VariantFormSet = inlineformset_factory(
    Product, ProductVariant,
    form=VariantForm,
    extra=1,
    min_num=1,
    can_delete=True,
    can_delete_extra=True
)

ImageFormSet = inlineformset_factory(
    Product, ProductImage,
    form=ImageForm,
    extra=1,
    can_delete=True,
    can_delete_extra=True
)

class CategoryForm(forms.ModelForm):
    class Meta:
      model = Category
      fields = ['name','description']

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