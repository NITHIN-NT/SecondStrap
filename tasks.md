🛒 Project Requirement To-Do List

1. Database & Models (Prerequisites)

[x] Design User Model (Custom user with profile image, phone).

[x] Design Address Model (ForeignKey to User).

[x] Design Product/Category Models (Include fields for is_listed and stock).

[x] Design Cart & CartItem Models.

[x] Design Order & OrderItem Models (Include custom order_id field, distinct from PK).

2. User Side: Profile Management

a. User Profile

[x] Create Profile View (Show User details + Profile Image + Default Address).

[x] Create Edit Profile Page (Separate URL/Page from View Profile).

[x] Backend: Implement OTP/Token verification logic for Email changes.

[x] Frontend: Add logic to trigger OTP modal when Email is edited.

[x] Implement "Change Password" functionality.

[x] Implement "Forgot Password" flow (Email trigger + Reset link).

b. Address Management

[x] Create "Add New Address" form.

[x] Create "Edit Address" form (Pre-fill existing data).

[x] Implement "Delete Address" (Soft delete or Hard delete).

[x] List all addresses on the Profile page.

3. User Side: Cart Management

c. Cart Functionality

[X] Backend Check: Verify if Product AND Category are listed/active before adding to cart.

[x] Logic: If Item exists in Cart -> Increment Quantity.

[ ] Logic: If Item exists in Wishlist -> Remove from Wishlist upon adding to Cart.

[x] Implement "Add to Cart" button on Product Details/Listing.

[x] Create Cart Listing Page.

[x] Implement Quantity Increment (+) button (Validate against Stock limits).

[x] Implement Quantity Decrement (-) button.

[x] Implement "Max Quantity per User" validation. --> doubt

[X] UI: Visually disable rows for "Out of Stock" items in the cart.

[x] Logic: Prevent "Proceed to Checkout" if the cart contains Out of Stock items.

[x] Implement "Remove Item" button.

4. User Side: Checkout & Payment

d. Checkout Page
[x] Display list of saved addresses with radio buttons.

[x] Add "Add New Address" / "Edit Address" buttons directly in checkout flow.

[x] Logic: Ensure one address is selected as Default for the order.

[ ] Order Summary Section:

[x] Display Product Image, Name, and Quantity.

[x Calculate Item Total (Price * Qty).

[x] Calculate Tax (if applicable).

[x] Apply Discount logic (Coupons/Offers).

[x] Show Final Price (Total + Tax + Shipping - Discount).

[x] Implement "Cash on Delivery" (COD) payment option.

[x] Backend: "Place Order" Logic (Create Order, Move CartItems to OrderItems, Clear Cart).

[ ] Success Page:

[x] Show "Thank You" message + Illustration.

[x] Button: "Go to Order Details".

[x] Button: "Continue Shopping".

5. User Side: Order Management

e. Order History

[x] Generate Custom Order ID (e.g., ORD-2025-XXXX, do not use database _id).

[x] Create Order Listing Page (Show Status, Date, ID, Total).

[ ] Implement Search bar for Orders.

[ ] Create Order Detail View (Full breakdown of items and pricing).

[ ] Cancel Logic:

[ ] Allow cancellation of full order or specific items.

[ ] Ask for "Reason for Cancellation" (Optional).

[ ] Inventory Update: Increment stock back to inventory upon cancellation.

[ ] Return Logic:

[ ] Show "Return" button only if status is "Delivered".

[ ] Ask for "Reason for Return" (Mandatory).

[ ] Implement PDF Invoice Generation & Download button.

6. Admin Side: Order Management

f. Admin Order Dashboard

[ ] List all Orders (Default Sort: Descending by Date).

[ ] Table Columns: OrderID, Date, User Info, Total, Status, Actions.

[ ] Create "Detailed View" for Admin (See shipping address, specific items).

[ ] Implement Status Change Dropdown (Pending -> Shipped -> Out for Delivery -> Delivered -> Cancelled).

[ ] Implement Search (By OrderID or Username).

[ ] Implement Filter (By Status, Date Range).

[ ] Implement Sorting.

[ ] Add "Clear Search/Filter" button.

[ ] Add Pagination to the Order List table.

7. Admin Side: Inventory

g. Inventory Management

[x] Create Inventory/Stock Overview page.

[x] (Optional based on requirements) Interface to manually adjust stock levels.



 if (isUpi) {
            placeOrderBtn.classList.add('loading');
            const formData = new FormData(form);
            
            // IMPORTANT: Ensure the coupon code is sent to the Razorpay order creation view
            if (promoInput.value.trim()) {
                formData.append('coupon_code', promoInput.value.trim());
            }

            try {
                const response = await fetch(createOrderUrl, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrfToken },
                    body: formData
                });

                const data = await response.json();

                if (!data.success) {
                    placeOrderBtn.classList.remove('loading');
                    toastr.error(data.error || 'Unable to create payment.');
                    return;
                }

                const options = {
                    key: data.razorpay_key_id,
                    amount: data.amount_paise,
                    currency: data.currency,
                    name: "SecondStrap",
                    order_id: data.razorpay_order_id,
                    handler: function (response) {
                        const callbackForm = document.createElement('form');
                        callbackForm.method = "POST";
                        callbackForm.action = "{% url 'razorpay_callback' %}";
                        
                        const fields = {
                            "csrfmiddlewaretoken": csrfToken,
                            "razorpay_payment_id": response.razorpay_payment_id,
                            "razorpay_order_id": response.razorpay_order_id,
                            "razorpay_signature": response.razorpay_signature,
                        };

                        for (let key in fields) {
                            const input = document.createElement('input');
                            input.type = "hidden";
                            input.name = key;
                            input.value = fields[key];
                            callbackForm.appendChild(input);
                        }
                        document.body.appendChild(callbackForm);
                        callbackForm.submit();
                    },
                    prefill: {
                        name: data.user_name,
                        email: data.user_email,
                        contact: data.user_phone
                    },
                    modal: { ondismiss: function() { placeOrderBtn.classList.remove('loading'); } }
                };

                const rzp = new Razorpay(options);
                rzp.on('payment.failed', function (resp) {
                    placeOrderBtn.classList.remove('loading');
                    toastr.error(`Payment failed: ${resp.error.description}`);
                    console.log(resp)
                }); 
                rzp.on('payment.failed', function (resp) {
                    axios.post(
                        "{% url 'payment_failed_logging' %}",
                        {
                            error: resp.error.description,
                            order_id: resp.error.metadata.order_id,
                        },
                        {
                            headers: {
                                "X-CSRFToken": csrfToken,
                                "Content-Type": "application/json",
                            }
                        }
                    ).catch((err) => {
                        console.error("Logging failed:", err);
                    }).finally(() => {
                        window.location.href = "{% url 'payment_failed_page' %}";
                    });

                }); 
                rzp.open();

            } catch (err) {
                placeOrderBtn.classList.remove('loading');
                toastr.error('Razorpay initialization failed.');
            }
        }

            