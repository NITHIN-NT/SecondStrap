from django.shortcuts import render

# Create your views here.
def wishlistView(request):
    return render(request,'wishlist/wishlist.html')