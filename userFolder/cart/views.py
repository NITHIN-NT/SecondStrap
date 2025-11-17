from django.shortcuts import render

# Create your views here.
def cartView(request):
    return render(request,'cart/cart.html')