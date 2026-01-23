# Project Technology Stack & Features

This document provides a comprehensive overview of the technologies, libraries, and tools used in the **SecondStrap** project.

## 🚀 Core Backend
- **Framework**: [Django 5.2.7](https://www.djangoproject.com/) (Python-based web framework)
- **App Server**: [Gunicorn](https://gunicorn.org/) (WSGI HTTP Server for UNIX)
- **Static Files**: [WhiteNoise](https://whitenoise.readthedocs.io/) (Radically simplified static file serving for Python web apps)
- **Environment**: `django-environ` (Environment variables management)
- **Authentication**: `django-allauth` (Integrated registration, login, and social account management)

## 🗄️ Database & Caching
- **Primary Database**: [PostgreSQL](https://www.postgresql.org/) (via `psycopg2`)
- **Key-Value Store**: [Redis](https://redis.io/) (used for caching and session management via `django-redis`)

## 💳 Payment Gateway
- **Razorpay**: Integrated for secure order processing and online payments.

## 🎨 Frontend Stack
- **Templating**: Django Template Language (DTL)
- **Styling**: Vanilla CSS with a focus on modern, responsive design.
- **Typography**: 
  - [Barlow Condensed](https://fonts.google.com/specimen/Barlow+Condensed) (Primary font)
  - VT323 (Monospace/Retro style font)
- **Icons**: [Boxicons](https://boxicons.com/)
- **Smooth Scrolling**: [Lenis](https://lenis.darkroom.engineering/)

### Javascript Libraries & Utilities
- **jQuery 3.7.1**: General-purpose DOM manipulation.
- **Axios**: Promised-based HTTP client for API calls (Offers, Cart updates, etc.).
- **Cropper.js**: Client-side image cropping for profile pictures.
- **SweetAlert2**: Beautiful, responsive, and customizable popup boxes.
- **Toastr**: Simple javascript toast notifications.

## 🛠️ Utilities & Processing
- **Image Handling**: [Pillow](https://python-pillow.org/), Cloudinary (Cloud storage integration)
- **Document Generation**:
  - `xhtml2pdf` / `ReportLab`: Converting HTML to PDF.
  - `pypdf`: PDF manipulation.
- **Excel Support**: `openpyxl` (Reading/writing Excel files).
- **SEO/Metadata**: Meta tags, semantic HTML headers, and dynamic breadcrumbs (`django-dynamic-breadcrumbs`).

## 🚢 Infrastructure & DevOps
- **Containerization**: [Docker](https://www.docker.com/) & Docker Compose.
- **CI/CD**: GitHub Actions (Automated build and deployment pipelines).
- **Process Management**: Docker multi-stage builds for optimized production images.

