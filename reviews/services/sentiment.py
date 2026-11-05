"""Sentiment analysis service for ScentScope perfume reviews.

This module provides reusable sentiment analysis for review messages. It is
intentionally modular so the engine can be replaced or improved later.

Classification approach:
- VADER (Valence Aware Dictionary and sEntiment Reasoner) performs the primary
  English-language classification of the written review into Positive, Neutral
  or Negative based on its compound score.
- Perfume-specific keyword lists are a *supplementary* signal: they are matched
  against the review text and stored as positive_keywords / negative_keywords
  for display. They do not override the VADER label.
- The star-based overall rating is mapped to a sentiment separately, and any
  disagreement with the written sentiment is flagged as a mismatch for staff
  review.

Limitations:
- VADER is tuned for English text. Non-English or mixed-language reviews may
  be misclassified.
- Sarcasm, irony and indirect opinions are not reliably detected.
- Automated sentiment analysis may not understand every nuance of perfume
  language. Results are best-effort estimates, not ground truth.
"""

from django.utils import timezone
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# VADER compound score thresholds. Centralized for easy adjustment.
POSITIVE_THRESHOLD = 0.05
NEGATIVE_THRESHOLD = -0.05

# Singleton analyzer instance (VADER is thread-safe for read-only scoring).
_analyzer = None

# Perfume-specific supplementary keywords. Matched case-insensitively as
# substrings against the written review. Ordered so longer/multi-word phrases
# are considered before shorter overlapping ones where sensible.
POSITIVE_KEYWORDS = [
    "long-lasting",
    "long lasting",
    "excellent projection",
    "great projection",
    "strong sillage",
    "elegant",
    "sophisticated",
    "refined",
    "luxurious",
    "fresh",
    "pleasant",
    "beautiful",
    "attractive",
    "refreshing",
    "captivating",
    "alluring",
    "gorgeous",
    "divine",
    "heavenly",
    "timeless",
    "classy",
    "compliments",
    "compliment",
    "love it",
    "amazing",
    "exquisite",
    "warm",
]

NEGATIVE_KEYWORDS = [
    "poor longevity",
    "weak projection",
    "weak",
    "overpowering",
    "expensive",
    "unpleasant",
    "synthetic",
    "disappointing",
    "fades",
    "fades quickly",
    "headache",
    "alcohol",
    "alcohol-heavy",
    "cheap",
    "harsh",
    "generic",
    "chemical",
    "cloying",
    "nauseating",
    "boring",
    "flat",
    "too strong",
]


def get_analyzer():
    """Return a shared VADER SentimentIntensityAnalyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentIntensityAnalyzer()
    return _analyzer


def classify_text_sentiment(text):
    """Classify a text string into Positive / Neutral / Negative.

    Returns:
        (label, score) where label is one of 'positive', 'neutral', 'negative'
        and score is the VADER compound score in [-1.0, 1.0]. Empty text is
        treated as neutral with a score of 0.0.
    """
    analyzer = get_analyzer()
    text = (text or "").strip()
    if not text:
        return "neutral", 0.0

    scores = analyzer.polarity_scores(text)
    compound = scores["compound"]

    if compound >= POSITIVE_THRESHOLD:
        label = "positive"
    elif compound <= NEGATIVE_THRESHOLD:
        label = "negative"
    else:
        label = "neutral"

    return label, compound


def classify_rating_sentiment(rating):
    """Classify an overall star rating (1-5) into sentiment.

    Mapping:
        4-5 stars -> positive
        3 stars   -> neutral
        1-2 stars -> negative
    """
    if rating >= 4:
        return "positive"
    if rating == 3:
        return "neutral"
    return "negative"


def extract_keywords(text):
    """Extract perfume-specific positive and negative keywords from a text.

    Returns:
        (positive_keywords, negative_keywords) as lists of unique matched
        keywords, in the order defined above.
    """
    text = (text or "").lower()
    positive = []
    for keyword in POSITIVE_KEYWORDS:
        if keyword.lower() in text and keyword not in positive:
            positive.append(keyword)
    negative = []
    for keyword in NEGATIVE_KEYWORDS:
        if keyword.lower() in text and keyword not in negative:
            negative.append(keyword)
    return positive, negative


def analyze_review(review):
    """Run sentiment analysis on a Review instance.

    Updates the existing ReviewSentiment record in place. Never creates a
    duplicate record. If analysis fails, marks the record as failed with an
    error message and increments attempts. The Review row itself is never
    touched or rolled back.

    Returns:
        The updated ReviewSentiment instance.
    """
    from reviews.models import ReviewSentiment

    analysis = getattr(review, "sentiment", None)
    if analysis is None:
        analysis = ReviewSentiment.objects.create(
            review=review,
            analysis_status=ReviewSentiment.Status.PENDING,
        )

    analysis.attempts = (analysis.attempts or 0) + 1
    analysis.analyzed_at = timezone.now()

    try:
        text_label, text_score = classify_text_sentiment(review.written_review)
        rating_label = classify_rating_sentiment(review.overall_rating)
        positive_keywords, negative_keywords = extract_keywords(
            review.written_review
        )

        analysis.sentiment_label = text_label
        analysis.sentiment_score = text_score
        analysis.rating_sentiment = rating_label
        analysis.positive_keywords = positive_keywords
        analysis.negative_keywords = negative_keywords
        analysis.analysis_status = ReviewSentiment.Status.SUCCESS
        analysis.error_message = ""

        # Mismatch: written sentiment and rating sentiment disagree.
        analysis.is_mismatch = text_label != rating_label

    except Exception as exc:  # noqa: BLE001 — capture any analysis failure
        analysis.analysis_status = ReviewSentiment.Status.FAILED
        analysis.error_message = str(exc)
        analysis.sentiment_label = ""
        analysis.sentiment_score = 0.0
        analysis.rating_sentiment = ""
        analysis.positive_keywords = []
        analysis.negative_keywords = []
        analysis.is_mismatch = False

    analysis.save()
    return analysis


def retry_failed_analyses(limit=None):
    """Retry sentiment analysis for all failed ReviewSentiment records.

    Args:
        limit: Maximum number of records to retry (None = all).

    Returns:
        (processed, succeeded, failed) counts.
    """
    from reviews.models import ReviewSentiment

    queryset = ReviewSentiment.objects.filter(
        analysis_status=ReviewSentiment.Status.FAILED
    ).select_related("review")

    if limit is not None:
        queryset = queryset[:limit]

    processed = 0
    succeeded = 0
    failed = 0

    for analysis in queryset:
        processed += 1
        try:
            analyze_review(analysis.review)
            if analysis.review.sentiment.analysis_status == ReviewSentiment.Status.SUCCESS:
                succeeded += 1
            else:
                failed += 1
        except Exception:  # noqa: BLE001
            failed += 1

    return processed, succeeded, failed
