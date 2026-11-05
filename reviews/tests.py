"""Tests for the reviews app."""

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from perfumes.models import Perfume, PerfumeBrand, FragranceFamily
from .models import Review, ReviewSentiment
from .tracking import generate_tracking_id
from .services.sentiment import (
    classify_text_sentiment,
    classify_rating_sentiment,
    extract_keywords,
    analyze_review,
)


class TrackingIdTests(TestCase):
    def test_tracking_id_format(self):
        tracking_id = generate_tracking_id()
        self.assertRegex(tracking_id, r"^SS-\d{4}-[A-Z2-9]{5}$")
        self.assertTrue(tracking_id.startswith(f"SS-{timezone.localdate().year}"))

    def test_tracking_id_unique(self):
        ids = {generate_tracking_id() for _ in range(50)}
        self.assertEqual(len(ids), 50)


class ReviewModelTests(TestCase):
    def setUp(self):
        self.brand = PerfumeBrand.objects.create(name="Test Brand")
        self.family = FragranceFamily.objects.create(name="Floral")
        self.perfume = Perfume.objects.create(
            perfume_name="Test Scent",
            brand=self.brand,
            fragrance_family=self.family,
            description="Desc.",
            top_notes="A",
            middle_notes="B",
            base_notes="C",
            concentration="edp",
            gender_category="unisex",
            price="50.00",
            volume_ml=50,
        )

    def test_review_creation(self):
        review = Review.objects.create(
            perfume=self.perfume,
            reviewer_name="Maya",
            reviewer_email="maya@example.com",
            overall_rating=5,
            longevity_rating=4,
            projection_rating=5,
            sillage_rating=3,
            fragrance_rating=5,
            value_for_money_rating=4,
            season_suitability="spring",
            occasion_suitability="daily",
            written_review="A lovely fresh scent that lasts well.",
        )
        self.assertRegex(review.tracking_id, r"^SS-\d{4}-[A-Z2-9]{5}$")
        self.assertEqual(str(review.overall_rating), "5")
        self.assertTrue(review.is_approved)

    def test_aspect_ratings(self):
        review = Review.objects.create(
            perfume=self.perfume,
            reviewer_name="Maya",
            reviewer_email="maya@example.com",
            overall_rating=5,
            longevity_rating=4,
            projection_rating=5,
            sillage_rating=3,
            fragrance_rating=5,
            value_for_money_rating=4,
            written_review="Nice.",
        )
        aspects = review.aspect_ratings
        self.assertEqual(aspects["longevity"], 4)
        self.assertEqual(aspects["value_for_money"], 4)


class SentimentServiceTests(TestCase):
    def setUp(self):
        self.brand = PerfumeBrand.objects.create(name="Test Brand")
        self.family = FragranceFamily.objects.create(name="Floral")
        self.perfume = Perfume.objects.create(
            perfume_name="Test Scent",
            brand=self.brand,
            fragrance_family=self.family,
            description="Desc.",
            top_notes="A",
            middle_notes="B",
            base_notes="C",
            concentration="edp",
            gender_category="unisex",
            price="50.00",
            volume_ml=50,
        )

    def test_text_sentiment_positive(self):
        label, score = classify_text_sentiment("This perfume is beautiful and fresh.")
        self.assertEqual(label, "positive")
        self.assertGreater(score, 0)

    def test_text_sentiment_negative(self):
        label, score = classify_text_sentiment("This is a disappointing, weak scent.")
        self.assertEqual(label, "negative")
        self.assertLess(score, 0)

    def test_text_sentiment_neutral(self):
        label, score = classify_text_sentiment("It is a perfume in a bottle.")
        self.assertEqual(label, "neutral")

    def test_empty_text_sentiment(self):
        label, score = classify_text_sentiment("")
        self.assertEqual(label, "neutral")
        self.assertEqual(score, 0.0)

    def test_rating_sentiment_mapping(self):
        self.assertEqual(classify_rating_sentiment(5), "positive")
        self.assertEqual(classify_rating_sentiment(4), "positive")
        self.assertEqual(classify_rating_sentiment(3), "neutral")
        self.assertEqual(classify_rating_sentiment(2), "negative")
        self.assertEqual(classify_rating_sentiment(1), "negative")

    def test_keyword_extraction(self):
        pos, neg = extract_keywords(
            "Long-lasting and elegant, but quite expensive and synthetic."
        )
        self.assertIn("long-lasting", pos)
        self.assertIn("elegant", pos)
        self.assertIn("expensive", neg)
        self.assertIn("synthetic", neg)

    def test_mismatch_detection(self):
        # 5 stars but strongly negative text => mismatch.
        review = Review.objects.create(
            perfume=self.perfume,
            reviewer_name="Maya",
            reviewer_email="maya@example.com",
            overall_rating=5,
            longevity_rating=1,
            projection_rating=1,
            sillage_rating=1,
            fragrance_rating=1,
            value_for_money_rating=1,
            written_review="Terrible, disappointing, weak and synthetic. Hate it.",
        )
        analysis = analyze_review(review)
        self.assertEqual(analysis.sentiment_label, "negative")
        self.assertEqual(analysis.rating_sentiment, "positive")
        self.assertTrue(analysis.is_mismatch)

    def test_no_mismatch(self):
        review = Review.objects.create(
            perfume=self.perfume,
            reviewer_name="Maya",
            reviewer_email="maya@example.com",
            overall_rating=5,
            longevity_rating=5,
            projection_rating=5,
            sillage_rating=5,
            fragrance_rating=5,
            value_for_money_rating=5,
            written_review="Beautiful, fresh and long-lasting. Love it.",
        )
        analysis = analyze_review(review)
        self.assertFalse(analysis.is_mismatch)

    def test_analysis_status_success(self):
        review = Review.objects.create(
            perfume=self.perfume,
            reviewer_name="Maya",
            reviewer_email="maya@example.com",
            overall_rating=4,
            longevity_rating=4,
            projection_rating=4,
            sillage_rating=4,
            fragrance_rating=4,
            value_for_money_rating=4,
            written_review="Pleasant scent.",
        )
        analysis = analyze_review(review)
        review.refresh_from_db()
        self.assertEqual(review.sentiment.analysis_status, "success")
        self.assertIsNotNone(review.sentiment.analyzed_at)
        self.assertIsInstance(review.sentiment.positive_keywords, list)


class ReviewViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.brand = PerfumeBrand.objects.create(name="Test Brand")
        self.family = FragranceFamily.objects.create(name="Floral")
        self.perfume = Perfume.objects.create(
            perfume_name="Test Scent",
            brand=self.brand,
            fragrance_family=self.family,
            description="Desc.",
            top_notes="A",
            middle_notes="B",
            base_notes="C",
            concentration="edp",
            gender_category="unisex",
            price="50.00",
            volume_ml=50,
            is_published=True,
        )

    def test_submit_review_form_renders(self):
        response = self.client.get(
            reverse("perfumes:reviews", kwargs={"slug": self.perfume.slug})
        )
        self.assertEqual(response.status_code, 200)

    def test_submit_review_creates_tracking_id(self):
        response = self.client.post(
            reverse("perfumes:reviews", kwargs={"slug": self.perfume.slug}),
            {
                "reviewer_name": "Maya",
                "reviewer_email": "maya@example.com",
                "overall_rating": "5",
                "longevity_rating": "4",
                "projection_rating": "5",
                "sillage_rating": "4",
                "fragrance_rating": "5",
                "value_for_money_rating": "4",
                "season_suitability": "spring",
                "occasion_suitability": "daily",
                "written_review": "A lovely fresh and long-lasting scent. Very pleasant.",
                "website": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        review = Review.objects.get(reviewer_name="Maya")
        self.assertRegex(review.tracking_id, r"^SS-\d{4}-[A-Z2-9]{5}$")
        self.assertTrue(review.sentiment.analysis_status in ("success", "failed"))

    def test_review_validation_min_length(self):
        response = self.client.post(
            reverse("perfumes:reviews", kwargs={"slug": self.perfume.slug}),
            {
                "reviewer_name": "Maya",
                "reviewer_email": "maya@example.com",
                "overall_rating": "5",
                "longevity_rating": "5",
                "projection_rating": "5",
                "sillage_rating": "5",
                "fragrance_rating": "5",
                "value_for_money_rating": "5",
                "written_review": "Short.",
                "website": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Review.objects.count(), 0)

    def test_honeypot_rejects_submission(self):
        response = self.client.post(
            reverse("perfumes:reviews", kwargs={"slug": self.perfume.slug}),
            {
                "reviewer_name": "Maya",
                "reviewer_email": "maya@example.com",
                "overall_rating": "5",
                "longevity_rating": "5",
                "projection_rating": "5",
                "sillage_rating": "5",
                "fragrance_rating": "5",
                "value_for_money_rating": "5",
                "written_review": "A lovely fresh and long-lasting scent. Very pleasant.",
                "website": "http://spam.example.com",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Review.objects.count(), 0)

    def test_success_page(self):
        review = Review.objects.create(
            perfume=self.perfume,
            reviewer_name="Maya",
            reviewer_email="maya@example.com",
            overall_rating=5,
            longevity_rating=5,
            projection_rating=5,
            sillage_rating=5,
            fragrance_rating=5,
            value_for_money_rating=5,
            written_review="Beautiful.",
        )
        response = self.client.get(
            reverse("reviews:success", kwargs={"tracking_id": review.tracking_id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, review.tracking_id)
        # Email never exposed.
        self.assertNotContains(response, "maya@example.com")

    def test_track_page_get(self):
        response = self.client.get(reverse("track"))
        self.assertEqual(response.status_code, 200)

    def test_track_lookup_found(self):
        review = Review.objects.create(
            perfume=self.perfume,
            reviewer_name="Maya",
            reviewer_email="maya@example.com",
            overall_rating=5,
            longevity_rating=5,
            projection_rating=5,
            sillage_rating=5,
            fragrance_rating=5,
            value_for_money_rating=5,
            written_review="Beautiful.",
        )
        response = self.client.post(
            reverse("track"), {"tracking_id": review.tracking_id.lower()}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, review.tracking_id)

    def test_track_lookup_not_found(self):
        response = self.client.post(
            reverse("track"), {"tracking_id": "SS-2026-ZZZZZ"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No review found")
