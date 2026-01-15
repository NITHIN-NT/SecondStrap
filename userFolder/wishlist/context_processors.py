from .models import *
def wishlist_count(request):
    if request.user.is_authenticated:
        return {
            "wishlist_count": WishlistItem.objects.filter(
                wishlist__user=request.user
            ).count()
        }
    return {"wishlist_count": 0}
