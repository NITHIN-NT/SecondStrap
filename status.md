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
- while loop in product post code 
'''
The while loop i used make a unique slug . means
if a **"shirt"** exist for one product
for the next first it add **"shirt-1"** like this . 
now i find the issue in this it hit database many times means it have N + 1 problem 
so to solve that i used **django-autoslug**
'''