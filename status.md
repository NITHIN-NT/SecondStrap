i think everything works

16/11/2025 - 11:31PM
“Everything is working as expected. Session handling, update, and add issues have been resolved.”

17/11/2025 - 2:58PM
"commit backup before major updates for develop"

17/11/2025 - 3:03PM
Week - 1 Pendings
- Sorting ( high to low )  // fixed - 8:16 PM
- remove <p> from description // fixed - 8 : 23 PM
- use list instead of cards in category listing // fixed - 8 : 43 PM
- minimum 3 image validation  // fixed - 9 : 07 PM
- session issue in user side
'''
> Added new SecureUserMixin in the Profile Page to reduce the reduntant use of the never_cache and LoginRequiredMixin
> In Project URLs changed from allauth.urls to allauth.socialaccount.providers.google.urls beacuse currently i only use the google .
> In Settings changed the Login_url to accounts/login and added ACCOUNT_AUTHNTICATED_LOGIN_REDIRECTS . 
> In accounts View Google_callback_safe view is added . If a user is logedin using google , the user can't see the login related pages again it redirect the user to the home_page
'''
- while loop in product post code 
'''
The while loop i used make a unique slug . means
if a **"shirt"** exist for one product
for the next first it add **"shirt-1"** like this . 
now i find the issue in this it hit database many times means it have N + 1 problem 
so to solve that i used **django-autoslug**
'''