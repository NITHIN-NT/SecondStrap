from django import forms
from .models import Offer, OfferType, DiscountType


class OfferForm(forms.ModelForm):
    class Meta:
        model = Offer
        exclude = ["created_at", "updated_at",'products', 'categories']

    def clean(self):
        cleaned_data = super().clean()

        offer_type = cleaned_data.get("offer_type")
        discount_type = cleaned_data.get("discount_type")
        discount_value = cleaned_data.get("discount_value")

        products = self.data.get("products")
        active = cleaned_data.get("active")
        display_home = cleaned_data.get("display_home")
        categories = self.data.get("categories")

        min_order_amount = cleaned_data.get("min_order_amount")
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if discount_type == DiscountType.PERCENTAGE and discount_value is not None and discount_value > 100:
            self.add_error("discount_value","Percentage discount cannot be greater than 100.")

        if offer_type == OfferType.PRODUCT and not products:
            self.add_error("offer_type","At least one product is required for a product-based offer.")

        if offer_type == OfferType.CATEGORY and not categories:
            self.add_error("offer_type","At least one category is required for a category-based offer.")

        if offer_type == OfferType.AMOUNT_THRESHOLD and not min_order_amount:
            self.add_error("min_order_amount","Minimum order amount is required for this offer type.")

        if start_date and end_date and end_date < start_date:
            self.add_error("end_date","End date cannot be before start date.")

        return cleaned_data
