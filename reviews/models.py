"""Database models for ScentScope reviews and sentiment analysis."""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from perfumes.models import Perfume

from .tracking import generate_unique_tracking_id


class Review(models.Model):
    """One perfume review submission from any visitor (login not required).

    Reviewer email is private and is never displayed publicly. Only someone
    holding the review's Tracking ID can look the submission up.
    """

    class SeasonSuitability(models.TextChoices):
        SPRING = "spring", "Spring"
        SUMMER = "summer", "Summer"
        AUTUMN = "autumn", "Autumn"
        WINTER = "winter", "Winter"
        ALL_SEASON = "all_season", "All Seasons"

    class OccasionSuitability(models.TextChoices):
        DAILY = "daily", "Daily / Everyday"
        OFFICE = "office", "Office / Work"
        EVENING = "evening", "Evening / Night Out"
        SPECIAL = "special", "Special Occasions"
        ROMANTIC = "romantic", "Romantic Dates"

    perfume = models.ForeignKey(
        Perfume, on_delete=models.CASCADE, related_name="reviews"
    )
    reviewer_name = models.CharField(max_length=100)
    reviewer_email = models.EmailField(
        help_text="Used only to send your Tracking ID. Never shown publicly."
    )
    tracking_id = models.CharField(
        max_length=16,
        unique=True,
        editable=False,
        db_index=True,
        default=generate_unique_tracking_id,
    )
    overall_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    longevity_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    projection_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    sillage_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    fragrance_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    value_for_money_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    season_suitability = models.CharField(
        max_length=20,
        choices=SeasonSuitability.choices,
        blank=True,
    )
    occasion_suitability = models.CharField(
        max_length=20,
        choices=OccasionSuitability.choices,
        blank=True,
    )
    written_review = models.TextField(
        help_text="Honest written review (10 to 2000 characters)."
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_approved = models.BooleanField(
        default=True,
        help_text="Unapproved reviews are hidden from public pages.",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["perfume", "created_at"]),
            models.Index(fields=["is_approved", "created_at"]),
        ]

    def __str__(self):
        return (
            f"{self.tracking_id} — {self.perfume.perfume_name} "
            f"({self.overall_rating}★)"
        )

    @property
    def aspect_ratings(self):
        """Return the characteristic ratings as a dict."""
        return {
            "longevity": self.longevity_rating,
            "projection": self.projection_rating,
            "sillage": self.sillage_rating,
            "fragrance": self.fragrance_rating,
            "value_for_money": self.value_for_money_rating,
        }


class ReviewSentiment(models.Model):
    """The stored result of analysing a review.

    A separate table keeps the visitor's review safe: if analysis fails, only
    this row records the failure and the review itself is never lost.
    """

    class Sentiment(models.TextChoices):
        POSITIVE = "positive", "Positive"
        NEUTRAL = "neutral", "Neutral"
        NEGATIVE = "negative", "Negative"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    review = models.OneToOneField(
        Review, on_delete=models.CASCADE, related_name="sentiment"
    )
    sentiment_label = models.CharField(
        max_length=10, choices=Sentiment.choices, blank=True
    )
    sentiment_score = models.FloatField(default=0.0)
    positive_keywords = models.JSONField(default=list, blank=True)
    negative_keywords = models.JSONField(default=list, blank=True)
    rating_sentiment = models.CharField(
        max_length=10, choices=Sentiment.choices, blank=True
    )
    is_mismatch = models.BooleanField(default=False)
    analysis_status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    error_message = models.TextField(blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    analyzed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "review sentiments"
        ordering = ["-review__created_at"]

    def __str__(self):
        return f"Sentiment for {self.review.tracking_id} ({self.analysis_status})"
