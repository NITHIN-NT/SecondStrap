from django import forms
from .models import Offer, OfferType, DiscountType


class OfferForm(forms.ModelForm):
    class Meta:
        model = Offer
        exclude = ["created_at", "updated_at",'products', 'categories']

    def clean(self):
        cleaned_data = super().clean()

        offer_type = cleaned_data.get("offer_type")
        discount_percentage = cleaned_data.get("discount_percentage")
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        products = self.data.getlist("products")      
        categories = self.data.getlist("categories")  

        if offer_type == OfferType.PRODUCT and not products:
            self.add_error("offer_type", "At least one product is required for a product-based offer.")

        if offer_type == OfferType.CATEGORY and not categories:
            self.add_error("offer_type", "At least one category is required for a category-based offer.")

        if start_date and end_date and end_date < start_date:
            self.add_error("end_date", "End date cannot be before start date.")

        if discount_percentage is not None and not (0 <= discount_percentage <= 100):
            self.add_error("discount_percentage", "Discount percentage must be between 0 and 100.")

        return cleaned_data