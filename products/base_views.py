from django.shortcuts import render,redirect
from django.views.generic import TemplateView,View
from django.db.models import Min
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages

from products.models import Product,Category
from offer.models import Offer
from .contact_models import ContactModel

class HomePageView(TemplateView):
    template_name = "products/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        products = (
            Product.objects.select_related("category")
            .prefetch_related("variants")
            .filter(is_active=True, variants__stock__gte=1)
            .annotate(offer_price=Min("variants__offer_price"))
            .order_by("?")[:4]
        )
        featured_products = (
            Product.objects.filter(is_featured=True, is_active=True)
            .prefetch_related("variants")
            .filter(is_active=True, variants__stock__gte=1)
            .annotate(offer_price=Min("variants__offer_price"))
            .order_by("?")[:4]
        )
        most_demanded = (
            Product.objects.filter(is_active=True)
            .prefetch_related("variants")
            .filter(is_active=True, variants__stock__gte=1)
            .annotate(offer_price=Min("variants__offer_price"))
            .order_by("?")[:4]
        )
        today = timezone.now().date()
        new_arrivals = (
            Product.objects.filter(created_at__date=today, is_active=True)
            .prefetch_related("variants")
            .filter(is_active=True, variants__stock__gte=1)
            .annotate(offer_price=Min("variants__offer_price"))
            .order_by("?")[:4]
        )

        categories = Category.objects.filter(is_active=True).prefetch_related(
            "products"
        )[:5]
        categories_for_template = []
        for category in categories:
            product = category.products.filter(
                is_active=True, image__isnull=False
            ).first()
            if product:
                categories_for_template.append(
                    {
                        "id": category.id,
                        "name": category.name,
                        "image": product.image,
                        "alt_text": product.name,
                    }
                )

        context["products"] = products
        context["featured_products"] = featured_products
        context["most_demanded"] = most_demanded
        context["new_arrivals"] = new_arrivals
        context["categories_for_template"] = categories_for_template

        return context


class AboutView(TemplateView):
    template_name = "products/about.html"

class TermsView(TemplateView):
    template_name = 'products/terms.html'
    
class PrivacyView(TemplateView):
    template_name = 'products/privacy_policy.html'
    
class ContactView(View):
    def get(self,request,*args, **kwargs):
        return render(request,'products/contact.html')
    
    def post(self,request,*args, **kwargs):
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        
        ContactModel.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message
        )
        messages.success(request,'Message received!')
        return redirect('Home_page_user')

def get_offers(request):
    '''
        This view is used to get the offers for the offer track
    '''
    offers_from_db = list(Offer.objects.filter(active=True,display_home=True).values_list('description',flat=True))
    return JsonResponse({'offers': offers_from_db})
