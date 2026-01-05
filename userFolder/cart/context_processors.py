from userFolder.cart.models import CartItems

def cart_count(request):
    if request.user.is_authenticated:
        return {
            "cart_count": CartItems.objects.filter(
                cart__user=request.user
            ).count()
        }
    return {"cart_count": 0}
