# SecondStrap

SecondStrap is a comprehensive, modular e-commerce web application built with Django. It features a robust architecture separating user-facing functionalities from administrative controls, ensuring a scalable and maintainable codebase.

## 🚀 Features

*   **User Management:** Secure authentication system using `django-allauth`, supporting Email and Google OAuth login.
*   **Product Management:** Detailed product handling with categorization, variants, and stock management.
*   **Shopping Experience:** Full-featured shopping cart, wishlist, and seamless checkout process.
*   **Order Management:** Comprehensive order tracking and history for users.
*   **Payments:** Integrated **Razorpay** payment gateway for secure transactions.
*   **Custom Admin Dashboard:** A dedicated, custom-built administration panel (separate from Django's default admin) for managing sales, products, users, coupons, and offers.
*   **Coupons & Offers:** Dynamic discount and promotion management system.
*   **Wallet & Referrals:** Customer loyalty features including a digital wallet and referral program.
*   **PDF Generation:** Invoice and report generation using `xhtml2pdf`.
*   **Cloud Storage:** Integration with **Cloudinary** for efficient management of static and media assets.

## 🛠 Tech Stack

*   **Backend:** Python 3.x, Django 5.2.7
*   **Database:** PostgreSQL (via `psycopg2` & `dj-database-url`) 
*   **Frontend:** Django Templates (HTML/CSS/JS)
*   **Authentication:** `django-allauth`
*   **Utilities:** `django-environ` (Configuration), `xhtml2pdf` (PDFs)

## 📂 Project Structure

The project follows a modular structure where user-related applications are grouped under `userFolder/`.

*   `SecondStrapProject/`: Core project settings and configuration.
*   `Admin/`: Custom administration dashboard logic.
*   `accounts/`: User authentication and custom user model.
*   `products/`: Product catalog and management.
*   `coupon/` & `offer/`: Discount logic.
*   `userFolder/`: Namespace for customer-centric apps:
    *   `cart/`: Shopping cart functionality. 
    *   `checkout/`: Order placement logic.
    *   `order/`: User order management.
    *   `payment/`: Payment gateway integration.
    *   `wallet/`, `wishlist/`, `referral/`, `review/`: Loyalty and feedback apps.

## ⚙️ Installation & Setup

### Prerequisites
*   Python 3.x
*   PostgreSQL
*   Git

### 1. Clone the Repository
```bash
git clone <repository-url>
cd SecondStrap
```

### 2. Create and Activate a Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
Create a `.env` file in the project root directory and add the following configurations:

```env
# Django Settings
SECRET_KEY=your_secret_key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (PostgreSQL)
DATABASE_URL=postgres://user:password@localhost:5432/your_db_name

# Payments (Razorpay)
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret

# Cloudinary (Media/Static)
CLOUD_NAME=your_cloud_name
API_KEY=your_api_key
API_SECRET=your_api_secret

# Email (SMTP)
EMAIL_HOST_USER=your_email@example.com
EMAIL_HOST_PASSWORD=your_email_password

# Google OAuth
client_id=your_google_client_id
secret=your_google_client_secret
```

### 5. Apply Migrations
```bash
python manage.py migrate
```

### 6. Run the Development Server
```bash
python manage.py runserver
```

Access the application at `http://127.0.0.1:8000/`.

## 🤝 Contributing

Contributions are welcome! Please fork the repository and create a pull request with your changes.

## 📄 License

[MIT License](LICENSE)
