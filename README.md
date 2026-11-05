# ScentScope — Smart Perfume Review, Feedback Collection and Analysis System

ScentScope is a Django-based web application that collects perfume reviews from
visitors, performs automatic sentiment analysis on the written reviews, and
provides staff with a comprehensive analytics dashboard to understand fragrance
opinion.

Visitors browse a catalogue of perfumes, submit detailed ratings (overall,
longevity, projection, sillage, fragrance quality, value for money) and written
reviews without creating an account, and receive a unique Tracking ID to revisit
their submission later. Staff members log in to a private dashboard to manage
the perfume catalogue, view all submitted reviews, see real-time sentiment
analysis results, and explore perfume rankings based on audience appreciation.

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Main Features](#2-main-features)
3. [Technology Stack](#3-technology-stack)
4. [System Architecture](#4-system-architecture)
5. [Database Schema](#5-database-schema)
6. [Application Workflow](#6-application-workflow)
7. [Installation Instructions](#7-installation-instructions)
8. [Migration Instructions](#8-migration-instructions)
9. [How to Create a Staff Account](#9-how-to-create-a-staff-account)
10. [How to Run the Application](#10-how-to-run-the-application)
11. [How to Run Tests](#11-how-to-run-tests)
12. [Screenshots](#12-screenshots)
13. [Future Enhancements](#13-future-enhancements)

---

## 1. Project Overview

### What ScentScope Is

ScentScope is a Smart Perfume Review, Feedback Collection and Analysis System.
It is a server-rendered Django web application that lets visitors browse a
catalogue of perfumes, submit star ratings and written reviews without creating
an account, and receive a unique Tracking ID (e.g. `SS-2026-A8K92`) to revisit
their submission later.

Staff members can log in to a private dashboard to manage the perfume catalogue
(add, edit, publish, unpublish, archive or delete perfumes), view all submitted
reviews, see real-time sentiment analysis results, and explore perfume rankings
based on audience appreciation.

### Why It Was Developed

ScentScope was developed to solve a common problem: collecting fragrance
feedback and turning raw ratings and written reviews into clear, actionable
insights. Star ratings alone do not tell the whole story — a 5-star rating with
a comment like "the scent is synthetic and fades quickly" reveals a mismatch
between the rating and the written opinion. ScentScope pairs every star rating
with automatic sentiment analysis to surface these insights.

---

## 2. Main Features

### Public Features

| Feature | Description |
|---------|-------------|
| Browse published perfumes | Visitors see all published perfumes with images, names, brands, fragrance families, concentrations, prices, and average ratings. |
| Search perfumes | Search by perfume name, brand, or fragrance notes. |
| Filter by fragrance family | Narrow results by olfactory family (Floral, Woody, Oriental, etc.). |
| Filter by concentration | Filter by EDT, EDP, EDC, or Parfum. |
| Filter by price range | Set a maximum price. |
| Filter by target audience | Filter by For Men, For Women, or Unisex. |
| Sort results | Newest, top rated, or price (low/high). |
| View perfume details | Dedicated page with notes pyramid (top/middle/base), performance details, rating breakdown, sentiment summary, and customer reviews. |
| Submit reviews without registration | No account or login required. Visitors rate overall, longevity, projection, sillage, fragrance quality and value for money, plus a written review. |
| Receive a unique Tracking ID | Every submission gets a unique ID (format: `SS-YYYY-XXXXX`) shown on the confirmation page. |
| Track submitted feedback | Visitors enter their Tracking ID at `/track/` to revisit their submission and see its sentiment result. |
| Submission confirmation page | After submitting, visitors see a confirmation page with their Tracking ID, perfume title, rating, sentiment, and a copy button. |

### Staff Features

| Feature | Description |
|---------|-------------|
| Secure staff login | Staff log in through `/accounts/login/`. Only users with staff status can access staff pages. |
| Add perfumes | Staff can add perfumes with name, brand, image, description, family, notes, concentration, gender, launch year, price, volume, longevity/sillage, availability, and publish status. |
| Edit perfumes | Staff can edit any perfume's details and replace its image. |
| Delete perfumes | Staff can delete perfumes with a confirmation screen showing how many reviews will also be removed. |
| Publish/unpublish perfumes | New perfumes are unpublished by default. Staff toggle publication so only published perfumes appear publicly. |
| View submitted reviews | Staff see all reviews with tracking ID, perfume, reviewer, ratings, sentiment, and submission date. |
| View perfume rankings | Staff see a ranked table of perfumes based on audience appreciation (ratings, sentiment, longevity, projection, value). |
| View rating and sentiment analytics | Charts and KPIs show rating distribution, sentiment split, review trends, and praise vs critiques. |
| Review rating-sentiment mismatches | Staff see mismatches where star rating and written sentiment disagree. |
| Retry failed sentiment analyses | Management command `retry_failed_sentiment` retries failed analyses. |
| Manage staff accounts | Staff accounts are created and managed through Django Admin at `/django-admin/`. |

> **Important:** Public registration is disabled. Staff accounts can only be
> created by an administrator through Django's superuser system or Django Admin.
> There is no public "Create account" or "Register" option on the website.

### Sentiment Analysis

- **Classification:** Written reviews are classified as Positive, Neutral, or Negative using VADER compound score thresholds (>= 0.05 positive, <= -0.05 negative, otherwise neutral).
- **Rating-based sentiment:** Overall star ratings are mapped separately: 4–5 stars = positive, 3 stars = neutral, 1–2 stars = negative.
- **Mismatch detection:** When text sentiment and rating sentiment disagree (e.g. 5 stars but negative written feedback), `is_mismatch` is flagged. Staff can see mismatch counts on the dashboard.
- **Perfume-specific keywords:** Supplementary keyword detection (e.g. "long-lasting", "elegant", "synthetic", "overpowering") is stored as positive/negative keyword lists for display. VADER remains the primary classifier; keywords are supplementary only.
- **Failure handling:** If sentiment analysis fails, the review row is never lost. The analysis record is marked "failed" with an error message, and staff can retry it later using the `retry_failed_sentiment` management command.
- **Limitations:** VADER is primarily designed for English text. Non-English or mixed-language reviews may not be classified accurately. Sarcasm, irony, and indirect opinions are not reliably detected. Automated sentiment analysis may not understand every nuance of perfume language. Results are best-effort estimates, not ground truth.

### Perfume Ranking

The ranking system uses a transparent weighted formula. All values are computed
from live SQLite database records — nothing is hardcoded or stored as a stale
score.

**Formula:**

```
Final Score =
    (Overall Rating Score × 0.35) +
    (Positive Sentiment Score × 0.25) +
    (Feedback Confidence × 0.15) +
    (Longevity Score × 0.10) +
    (Projection Score × 0.10) +
    (Value Score × 0.05)
```

**Components (all normalized to 0–100):**

| Component | Formula | Range |
|-----------|---------|-------|
| Overall Rating Score | (Average overall rating / 5) × 100 | 0–100 |
| Positive Sentiment % | (Positive analysed reviews / Total analysed reviews) × 100 | 0–100 |
| Feedback Confidence | min(Review count / 20, 1) × 100 | 0–100 |
| Longevity Score | (Average longevity rating / 5) × 100 | 0–100 |
| Projection Score | (Average projection rating / 5) × 100 | 0–100 |
| Value Score | (Average value-for-money rating / 5) × 100 | 0–100 |

**Thresholds:**

- `MIN_REVIEWS_FOR_RANKING = 5`: A perfume must have at least 5 reviews to appear in the reliable ranking. Perfumes with fewer than 5 reviews show an "Insufficient data" label.
- `CONFIDENCE_DENOMINATOR = 20`: Feedback confidence caps at 100% when a perfume has 20 or more reviews.

**Example calculation** for a perfume with 8 reviews, average rating 4.625,
average longevity 4.5, average projection 4.2, average value 4.0, and 6 out of
8 analysed as positive:

- Overall Rating Score = (4.625 / 5) × 100 = 92.5
- Positive Sentiment % = (6 / 8) × 100 = 75.0
- Feedback Confidence = min(8 / 20, 1) × 100 = 40.0
- Longevity Score = (4.5 / 5) × 100 = 90.0
- Projection Score = (4.2 / 5) × 100 = 84.0
- Value Score = (4.0 / 5) × 100 = 80.0
- Final Score = (92.5 × 0.35) + (75.0 × 0.25) + (40.0 × 0.15) + (90.0 × 0.10) + (84.0 × 0.10) + (80.0 × 0.05)
  = 32.375 + 18.75 + 6.0 + 9.0 + 8.4 + 4.0 = **78.525**

---

## 3. Technology Stack

| Technology | Purpose |
|------------|---------|
| HTML5 | Semantic page structure for all public and staff pages. |
| CSS3 | Styling with a premium ivory/cream, charcoal and gold aesthetic, responsive layouts, and modern typography (Playfair Display + Inter). |
| JavaScript (Vanilla) | Interactive UI behaviour: mobile navigation, staff sidebar, star rating widget, character counter, copy-to-clipboard, and Chart.js integration. |
| Python 3 | Backend programming language. |
| Django 6.1.2 | Web framework handling routing, templates, forms, database ORM, authentication, and admin. |
| SQLite | File-based relational database (`db.sqlite3`). No separate database server required. |
| VADER (vaderSentiment) | Lexicon-based sentiment analysis for English text, producing compound scores in [-1.0, 1.0]. |
| Chart.js | Interactive charts for the staff dashboard (line, doughnut, bar charts). |
| Pillow | Image handling for uploaded perfume images. |

No Node.js, MongoDB, React, or external AI APIs are used or required.

---

## 4. System Architecture

ScentScope follows a clean separation of concerns:

- **`perfumes` app** — Perfume catalogue models (`Perfume`, `PerfumeBrand`, `FragranceFamily`, `PerfumeImage`), staff/public views, forms, services (annotated queries), validators, URLs, admin.
- **`reviews` app** — Review and sentiment models (`Review`, `ReviewSentiment`), tracking ID generation (`SS-YYYY-XXXXX`), review form, VADER sentiment service, views (submit, success, track), admin, management command (`retry_failed_sentiment`).
- **`analytics` app** — Staff dashboard views, Chart.js JSON endpoints, analytics services (sentiment breakdown, keyword leaderboard, rating breakdown, trend charts), and the perfume ranking service.
- **`accounts` app** — Staff authentication (login/logout), public registration disabled, email verification model.
- **`scentscope`** — Django project configuration (settings, URLs, WSGI/ASGI).

Business logic (sentiment analysis, ranking, analytics queries) lives in dedicated service modules, not inside views. Templates use a shared `base.html` with reusable partials (perfume card, pagination, sentiment badge).

---

## 5. Database Schema

ScentScope uses SQLite (`db.sqlite3`). The main models:

### Perfume (`perfumes` app)

| Field | Type | Description |
|-------|------|-------------|
| `id` | BigAutoField | Primary key |
| `perfume_name` | CharField (200) | Perfume name |
| `slug` | SlugField (220, unique) | URL-friendly identifier (auto-generated) |
| `brand` | FK → PerfumeBrand | Brand/perfume house (PROTECT) |
| `description` | TextField | Perfume description |
| `fragrance_family` | FK → FragranceFamily | Olfactory family (PROTECT) |
| `top_notes` | CharField (200) | Comma-separated top notes |
| `middle_notes` | CharField (200) | Comma-separated middle/heart notes |
| `base_notes` | CharField (200) | Comma-separated base notes |
| `concentration` | CharField (10) | EDT / EDP / EDC / Parfum |
| `gender_category` | CharField (10) | Unisex / Men / Women |
| `launch_year` | PositiveSmallIntegerField | Launch year (not future) |
| `price` | DecimalField (10,2) | Retail price |
| `volume_ml` | PositiveSmallIntegerField | Bottle size in ml |
| `image` | ImageField | Main perfume image (uploaded to `media/perfumes/`) |
| `longevity_category` | CharField (15) | Short / Moderate / Long / Very Long |
| `sillage_category` | CharField (15) | Soft / Moderate / Strong / Intense |
| `availability_status` | CharField (20) | In Stock / Limited / Discontinued |
| `is_published` | BooleanField | Visible to public (default False) |
| `created_at`, `updated_at` | DateTimeField | Automatic timestamps |

### PerfumeBrand

| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField (100) | Brand name |
| `slug` | SlugField (120, unique) | URL-friendly identifier |
| `country` | CharField (100) | Country of origin |
| `founded_year` | PositiveSmallIntegerField | Founding year |
| `description`, `website` | TextField / URLField | Brand details |
| `is_active` | BooleanField | Active brand |
| `created_at`, `updated_at` | DateTimeField | Timestamps |

### FragranceFamily

| Field | Type | Description |
|-------|------|-------------|
| `name` | CharField (80) | Family name (e.g. Floral, Woody) |
| `slug` | SlugField (100, unique) | URL-friendly identifier |
| `description` | TextField | Family description |
| `is_active` | BooleanField | Active family |
| `created_at` | DateTimeField | Timestamp |

### PerfumeImage

| Field | Type | Description |
|-------|------|-------------|
| `perfume` | FK → Perfume | Parent perfume (CASCADE) |
| `image` | ImageField | Gallery image (uploaded to `media/perfumes/gallery/`) |
| `alt_text` | CharField (200) | Alt text |
| `is_primary` | BooleanField | Primary flag |
| `uploaded_at` | DateTimeField | Timestamp |

### Review (`reviews` app)

| Field | Type | Description |
|-------|------|-------------|
| `id` | BigAutoField | Primary key |
| `perfume` | FK → Perfume | Perfume being reviewed (CASCADE) |
| `reviewer_name` | CharField (100) | Visitor's name |
| `reviewer_email` | EmailField | Visitor's email (private, never public) |
| `tracking_id` | CharField (16, unique) | Unique ID `SS-YYYY-XXXXX` |
| `overall_rating` | PositiveSmallIntegerField | 1–5 stars |
| `longevity_rating` | PositiveSmallIntegerField | 1–5 stars |
| `projection_rating` | PositiveSmallIntegerField | 1–5 stars |
| `sillage_rating` | PositiveSmallIntegerField | 1–5 stars |
| `fragrance_rating` | PositiveSmallIntegerField | 1–5 stars |
| `value_for_money_rating` | PositiveSmallIntegerField | 1–5 stars |
| `season_suitability` | CharField (20) | Spring / Summer / Autumn / Winter / All Seasons |
| `occasion_suitability` | CharField (20) | Daily / Office / Evening / Special / Romantic |
| `written_review` | TextField | Written review (10–2000 chars) |
| `created_at`, `updated_at` | DateTimeField | Timestamps |
| `is_approved` | BooleanField | Approved for public display (default True) |

### ReviewSentiment (`reviews` app)

| Field | Type | Description |
|-------|------|-------------|
| `review` | OneToOneField → Review | Linked review (CASCADE) |
| `sentiment_label` | CharField (10) | Positive / Neutral / Negative |
| `sentiment_score` | FloatField | VADER compound score (−1.0 to 1.0) |
| `positive_keywords` | JSONField | Detected positive keywords |
| `negative_keywords` | JSONField | Detected negative keywords |
| `rating_sentiment` | CharField (10) | Sentiment from star rating |
| `is_mismatch` | BooleanField | Text/rating sentiment disagree |
| `analysis_status` | CharField (10) | Pending / Success / Failed |
| `error_message` | TextField | Error if analysis failed |
| `attempts` | PositiveSmallIntegerField | Analysis attempts |
| `analyzed_at` | DateTimeField | Analysis completion time |

### Relationships

- **Perfume → Review:** One perfume can have many reviews (one-to-many, CASCADE).
- **Review → ReviewSentiment:** One review has one sentiment analysis (one-to-one, CASCADE).
- **PerfumeBrand → Perfume:** One brand can have many perfumes (PROTECT on delete).
- **FragranceFamily → Perfume:** One family can have many perfumes (PROTECT on delete).

---

## 6. Application Workflow

### Visitor Workflow

1. **Open the home page** at `http://127.0.0.1:8000/`.
2. **Browse perfumes** — published perfumes appear as cards with images, names, brands, families, and ratings. Use search and filters to narrow results.
3. **Select a perfume** — click a card to view its details, notes pyramid, performance, rating breakdown and customer reviews.
4. **Submit a review** — click "Write a review" and rate overall, longevity, projection, sillage, fragrance quality and value for money (1–5 each), pick season/occasion, and write a review. No account required.
5. **Receive the tracking ID** — after submission, you see a confirmation page with your unique Tracking ID (e.g. `SS-2026-A8K92`). Copy it.
6. **Track your submission** — go to `/track/`, enter your Tracking ID, and view your submission details and sentiment result.

### Staff Workflow

1. **Log in** at `http://127.0.0.1:8000/accounts/login/` using staff credentials.
2. **Open the dashboard** at `http://127.0.0.1:8000/staff/` to see KPIs, charts and recent reviews.
3. **Add perfumes** — go to `/staff/perfumes/add/` and fill in the perfume details. New perfumes are unpublished by default.
4. **Publish perfumes** — toggle the "Publish publicly" checkbox or use the Publish button in the perfume list.
5. **View reviews** — see all submissions in the dashboard's recent reviews panel.
6. **Review sentiment analysis** — check sentiment breakdown, mismatch counts, and per-perfume sentiment data.
7. **View perfume rankings** — see the ranked table of perfumes based on audience appreciation scores.
8. **Manage accounts** — create staff users through Django Admin at `/django-admin/`.

---

## 7. Installation Instructions

Follow these steps to set up and run ScentScope.

### Step 1: Open the Project Folder

Open the project folder in VS Code or your preferred editor.

### Step 2: Create a Virtual Environment

```powershell
python -m venv venv
```

### Step 3: Activate the Virtual Environment

```powershell
.\venv\Scripts\Activate
```

### Step 4: Install Dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

This installs Django 6.1.2, Pillow, python-dotenv, and vaderSentiment.

### Step 5: Configure Environment Variables

ScentScope loads secrets from a `.env` file in the project root. A template is provided at `.env.example`.

```powershell
copy .env.example .env
```

Open `.env` and update values as needed. For development, the console email backend prints emails to the terminal.

**Important:** Never commit `.env`. Set `DJANGO_DEBUG=False` and real `DJANGO_SECRET_KEY` / `DJANGO_ALLOWED_HOSTS` before deploying to production.

### Step 6: Apply Database Migrations

```powershell
python manage.py migrate
```

This creates all SQLite tables defined in the project's migrations.

### Step 7: Create the First Superuser

```powershell
python manage.py createsuperuser
```

This superuser has full staff access and can log in to the website and Django Admin.

### Step 8: Run the Project

```powershell
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

---

## 8. Migration Instructions

The project ships with initial migrations for the `perfumes` and `reviews` apps:

- `perfumes/migrations/0001_initial.py` — PerfumeBrand, FragranceFamily, Perfume, PerfumeImage.
- `perfumes/migrations/0002_*.py` — Made `Perfume.image` and `PerfumeImage.image` blank=True.
- `reviews/migrations/0001_initial.py` — Review, ReviewSentiment.

To apply:

```powershell
python manage.py migrate
```

If you need to reset the database during development:

```powershell
# Stop the server, delete db.sqlite3, then re-apply:
Remove-Item db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

There is no meaningful conversion of movie data to perfume data; the old ReelScope movie/feedback models were removed and replaced by the new perfume/review models.

---

## 9. How to Create a Staff Account

Public staff registration is **disabled**. Staff accounts must be created through Django's superuser/admin system.

### First Staff Account — Superuser

```powershell
python manage.py createsuperuser
```

Follow the prompts to set a username, email, and password. After creating the superuser:

1. Start the server: `python manage.py runserver`
2. Open `http://127.0.0.1:8000/accounts/login/`
3. Log in with your superuser credentials.
4. You can now access the staff dashboard at `http://127.0.0.1:8000/staff/`.

### Creating Additional Staff Accounts

1. Start the server and log in to Django Admin: `http://127.0.0.1:8000/django-admin/`
2. Use your superuser credentials.
3. Click **Users** under the "Auth" section, then **Add User**.
4. Enter username and password, click **Save**.
5. Click the new user's name, check **Staff status** (`is_staff`), and click **Save**.

The new staff member can now log in and access staff pages. Public visitors cannot create staff accounts through the website.

---

## 10. How to Run the Application

With the virtual environment activated:

```powershell
python manage.py runserver
```

Then open `http://127.0.0.1:8000/`.

Key URLs:

| URL | Page | Access |
|-----|------|--------|
| `/` | Home page | Public |
| `/perfumes/` | Perfume listing (search, filter, paginate) | Public |
| `/perfumes/<slug>/` | Perfume detail page | Public (published perfumes only) |
| `/perfumes/<slug>/reviews/` | Review submission form | Public |
| `/reviews/success/<tracking_id>/` | Review confirmation page | Public |
| `/track/` | Review tracking lookup | Public |
| `/accounts/login/` | Staff login | Public (login form) |
| `/accounts/logout/` | Logout | Authenticated users |
| `/accounts/register/` | Registration (disabled) | Redirects to login |
| `/staff/` | Staff dashboard | Staff only |
| `/staff/data/summary/` | Summary stats JSON | Staff only |
| `/staff/data/ratings/` | Perfume ratings chart JSON | Staff only |
| `/staff/data/sentiment/` | Sentiment by perfume JSON | Staff only |
| `/staff/data/trends/` | Review trends JSON | Staff only |
| `/staff/perfumes/` | Staff perfume management list | Staff only |
| `/staff/perfumes/add/` | Add perfume | Staff only |
| `/staff/perfumes/<pk>/edit/` | Edit perfume | Staff only |
| `/staff/perfumes/<pk>/delete/` | Delete perfume | Staff only |
| `/staff/perfumes/<pk>/toggle-publish/` | Publish/unpublish | Staff only |
| `/django-admin/` | Django Admin | Staff/superuser only |

---

## 11. How to Run Tests

ScentScope uses Django's built-in test framework. Run from the project root with the virtual environment activated:

### System Check

```powershell
python manage.py check
```

### Run All Tests

```powershell
python manage.py test
```

This runs all test cases in the `tests.py` files of each app (perfumes, reviews, analytics, accounts), covering model creation, search/filters, review submission, validation, tracking IDs, sentiment analysis, mismatch detection, ranking calculations, staff authentication, review approval, chart endpoints, access control, and empty-database behavior.

---

## 12. Screenshots

Add screenshots here of:

- Home page (hero, featured perfume, new arrivals, top rated)
- Perfume listing page (search, filters, cards)
- Perfume detail page (image, notes, rating, reviews)
- Review submission form (6 rating controls, written review)
- Review confirmation page (Tracking ID)
- Tracking lookup page
- Staff dashboard (KPIs, charts, ranking table)
- Staff perfume management (add/edit/publish)

---

## 13. Future Enhancements

- Perfume recommendation engine based on user preferences
- Seasonal and occasion-based discovery
- CSV/PDF export of analytics reports
- Public user profiles and review history
- Email delivery of Tracking IDs (SMTP configuration required)
- Image gallery with multiple photos per perfume
- Brand and family detail pages
- Advanced sentiment aspects (sillage, longevity, value sub-sentiments)

---

*ScentScope — Fragrance feedback, decoded. Every rating and review becomes a clear signal.*
