class Cart():
    def __init__(self,request):
        self.session = request.session

        # Get the current session key if it exists
        cart = self.session.get('cart_id')

        if 'cart_id' not in request.session:
            cart = self.session['cart_id'] = {}

        self.cart = cart
    def add(self,product):
        product_id = product.id

        if product_id in self.cart:
            pass
        else:
            self.cart[product_id] = {'price' : product.offer_price}  

        self.session.modified = True        