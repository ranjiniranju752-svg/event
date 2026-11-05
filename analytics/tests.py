"""Tests for the analytics app."""

from django.test import TestCase, Client

from perfumes.models import Perfume, PerfumeBrand, FragranceFamily
from reviews.models import Review, ReviewSentiment
from .services import ranking


def make_perfume(name, brand_name="Brand", family_name="Floral"):
    brand, _ = PerfumeBrand.objects.get_or_create(name=brand_name)
    family, _ = FragranceFamily.objects.get_or_create(name=family_name)
    return Perfume.objects.create(
        perfume_name=name,
        brand=brand,
        fragrance_family=family,
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


def make_review(perfume, overall, longevity, projection, sillage, fragrance, value, text, sentiment_label):
    review = Review.objects.create(
        perfume=perfume,
        reviewer_name="Tester",
        reviewer_email="tester@example.com",
        overall_rating=overall,
        longevity_rating=longevity,
        projection_rating=projection,
        sillage_rating=sillage,
        fragrance_rating=fragrance,
        value_for_money_rating=value,
        written_review=text,
    )
    ReviewSentiment.objects.create(
        review=review,
        sentiment_label=sentiment_label,
        sentiment_score=0.5 if sentiment_label == "positive" else -0.5,
        rating_sentiment="positive" if overall >= 4 else ("neutral" if overall == 3 else "negative"),
        is_mismatch=False,
        analysis_status=ReviewSentiment.Status.SUCCESS,
        positive_keywords=[],
        negative_keywords=[],
    )
    return review


class RankingTests(TestCase):
    def test_weights_sum_to_one(self):
        total = (
            ranking.WEIGHT_OVERALL
            + ranking.WEIGHT_SENTIMENT
            + ranking.WEIGHT_CONFIDENCE
            + ranking.WEIGHT_LONGEVITY
            + ranking.WEIGHT_PROJECTION
            + ranking.WEIGHT_VALUE
        )
        self.assertAlmostEqual(total, 1.0)

    def test_min_review_threshold_excludes(self):
        perfume = make_perfume("Rare Scent")
        # Only 4 reviews -> below MIN_REVIEWS_FOR_RANKING (5).
        for i in range(4):
            make_review(perfume, 5, 5, 5, 5, 5, 5, "Great scent.", "positive")
        results = ranking.calculate_perfume_scores()
        result = next(r for r in results if r["perfume"].pk == perfume.pk)
        self.assertFalse(result["ranking_available"])
        self.assertIsNone(result["rank"])
        self.assertIn("more", result["insufficient_reason"])

    def test_min_review_threshold_includes(self):
        perfume = make_perfume("Popular Scent")
        for i in range(5):
            make_review(perfume, 5, 5, 5, 5, 5, 5, "Great scent.", "positive")
        results = ranking.calculate_perfume_scores()
        result = next(r for r in results if r["perfume"].pk == perfume.pk)
        self.assertTrue(result["ranking_available"])
        self.assertEqual(result["rank"], 1)
        self.assertIsNotNone(result["final_score"])

    def test_ranking_formula(self):
        perfume = make_perfume("Formula Scent")
        # 5 reviews, all 5 stars, all positive sentiment.
        for i in range(5):
            make_review(perfume, 5, 5, 5, 5, 5, 5, "Great scent.", "positive")
        results = ranking.calculate_perfume_scores()
        result = next(r for r in results if r["perfume"].pk == perfume.pk)
        expected = (
            100 * ranking.WEIGHT_OVERALL
            + 100 * ranking.WEIGHT_SENTIMENT
            + (5 / ranking.CONFIDENCE_DENOMINATOR) * 100 * ranking.WEIGHT_CONFIDENCE
            + 100 * ranking.WEIGHT_LONGEVITY
            + 100 * ranking.WEIGHT_PROJECTION
            + 100 * ranking.WEIGHT_VALUE
        )
        self.assertAlmostEqual(result["final_score"], round(expected, 2), places=1)

    def test_insufficient_reason_for_no_sentiment(self):
        perfume = make_perfume("No Sentiment Scent")
        # 5 reviews but none analysed.
        for i in range(5):
            Review.objects.create(
                perfume=perfume,
                reviewer_name="Tester",
                reviewer_email="tester@example.com",
                overall_rating=5,
                longevity_rating=5,
                projection_rating=5,
                sillage_rating=5,
                fragrance_rating=5,
                value_for_money_rating=5,
                written_review="Great scent.",
            )
        results = ranking.calculate_perfume_scores()
        result = next(r for r in results if r["perfume"].pk == perfume.pk)
        self.assertFalse(result["ranking_available"])
        self.assertIn("sentiment", result["insufficient_reason"].lower())

    def test_get_perfume_ranking_returns_none_for_unpublished(self):
        perfume = make_perfume("Hidden", brand_name="X", family_name="Y")
        perfume.is_published = False
        perfume.save()
        self.assertIsNone(ranking.get_perfume_ranking(perfume))


class AnalyticsViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.perfume = make_perfume("Dashboard Scent")
        for i in range(5):
            make_review(self.perfume, 5, 5, 5, 5, 5, 5, "Great scent.", "positive")

    def test_dashboard_requires_staff(self):
        response = self.client.get("/staff/")
        self.assertEqual(response.status_code, 302)

    def test_chart_endpoints(self):
        from django.contrib.auth.models import User
        user = User.objects.create_superuser("staff", "s@example.com", "pass")
        self.client.login(username="staff", password="pass")
        for endpoint in [
            "/staff/data/summary/",
            "/staff/data/ratings/",
            "/staff/data/sentiment/",
            "/staff/data/trends/",
        ]:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "application/json")

    def test_summary_counts(self):
        from django.contrib.auth.models import User
        user = User.objects.create_superuser("staff2", "s2@example.com", "pass")
        self.client.login(username="staff2", password="pass")
        data = self.client.get("/staff/data/summary/").json()
        self.assertEqual(data["total_perfumes"], 1)
        self.assertEqual(data["total_reviews"], 5)
        self.assertEqual(data["counts"]["positive"], 5)
