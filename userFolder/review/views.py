import json

from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.db import transaction
from userFolder.order.models import OrderItem

from products.models import Product
from .models import Review


@require_http_methods(["POST"])
@csrf_protect
def submit_review(request):

    if not request.user.is_authenticated:
        return JsonResponse({"message": "Login to add Review"},status=401)

    try:
        data = json.loads(request.body)

        product_id = data.get("product_id")
        rating = data.get("rating")
        comment = data.get("comment", "").strip()

        if not product_id or rating is None:
            return JsonResponse({"message": "Product ID and rating are required"},status=400)

        try:
            rating = int(rating)
            if rating not in range(1, 6):
                raise ValueError
        except ValueError:
            return JsonResponse({"message": "Rating must be an integer between 1 and 5"},status=400)

        product = get_object_or_404(Product, id=product_id)
    
        purchased = OrderItem.objects.filter(order__user=request.user,variant__product=product).exists()    
        if not purchased :
            return JsonResponse({"message":"Please purchase this to add review"},status=400)
        
        
        review, created = Review.objects.update_or_create(
            product=product,
            user=request.user,
            defaults={
                "rating": rating,
                "comment": comment
            }
        )

        return JsonResponse(
            {
                "message": "Review created" if created else "Review updated",
                "review_id": review.id,
                "action": "created" if created else "updated"
            },
            status=201 if created else 200
        )

    except json.JSONDecodeError:
        return JsonResponse({"message": "Invalid JSON"}, status=400)

    except Exception:
        print("submit_review failed")
        return JsonResponse(
            {"message": "Something went wrong"},
            status=500
        )
