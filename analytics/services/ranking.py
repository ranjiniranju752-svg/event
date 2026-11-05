"""Perfume ranking service.

Implements a transparent, explainable weighted scoring system for perfumes
based on actual reviews and sentiment analysis records stored in SQLite.

Formula:
    Final Score =
        (Overall Rating Score × 0.35) +
        (Positive Sentiment Score × 0.25) +
        (Feedback Confidence × 0.15) +
        (Longevity Score × 0.10) +
        (Projection Score × 0.10) +
        (Value Score × 0.05)

Components (all normalized to 0–100):
    Overall Rating Score   = (Average overall rating / 5) × 100
    Positive Sentiment %   = (Positive analysed reviews / Total analysed reviews) × 100
    Feedback Confidence    = min(Review count / CONFIDENCE_DENOMINATOR, 1) × 100
    Longevity Score        = (Average longevity rating / 5) × 100
    Projection Score       = (Average projection rating / 5) × 100
    Value Score            = (Average value-for-money rating / 5) × 100

Minimum review threshold (centralized):
    MIN_REVIEWS_FOR_RANKING = 5  (perfumes below this are excluded from ranking)
    CONFIDENCE_DENOMINATOR   = 20 (confidence caps at 100% at 20 submissions)

All values are computed from live database records. Nothing is hardcoded or
stored as a stale score on the Perfume model.
"""

from django.db.models import Avg, Count, Q

from perfumes.models import Perfume
from reviews.models import Review, ReviewSentiment

# Centralized thresholds — easy to adjust in one place.
MIN_REVIEWS_FOR_RANKING = 5
CONFIDENCE_DENOMINATOR = 20

# Weighted formula constants (must sum to 1.0).
WEIGHT_OVERALL = 0.35
WEIGHT_SENTIMENT = 0.25
WEIGHT_CONFIDENCE = 0.15
WEIGHT_LONGEVITY = 0.10
WEIGHT_PROJECTION = 0.10
WEIGHT_VALUE = 0.05

SUCCESS = ReviewSentiment.Status.SUCCESS


def _perfume_review_stats():
    """Return a queryset of perfumes annotated with review statistics.

    Each perfume is annotated with:
        total_reviews          — count of all Review rows
        approved_reviews       — count of approved Review rows
        average_overall_rating — average overall rating (may be None)
        avg_longevity          — average longevity rating
        avg_projection         — average projection rating
        avg_value              — average value-for-money rating
        analyzed_reviews       — count of successfully analysed reviews
        positive_reviews       — count of positive text sentiment
        negative_reviews       — count of negative text sentiment
        neutral_reviews        — count of neutral text sentiment
    """
    return (
        Perfume.objects.filter(is_published=True)
        .annotate(
            total_reviews=Count("reviews", distinct=True),
            average_overall_rating=Avg("reviews__overall_rating"),
            avg_longevity=Avg("reviews__longevity_rating"),
            avg_projection=Avg("reviews__projection_rating"),
            avg_value=Avg("reviews__value_for_money_rating"),
            analyzed_reviews=Count(
                "reviews__sentiment",
                filter=Q(reviews__sentiment__analysis_status=SUCCESS),
                distinct=True,
            ),
            positive_reviews=Count(
                "reviews__sentiment",
                filter=Q(
                    reviews__sentiment__analysis_status=SUCCESS,
                    reviews__sentiment__sentiment_label="positive",
                ),
                distinct=True,
            ),
            negative_reviews=Count(
                "reviews__sentiment",
                filter=Q(
                    reviews__sentiment__analysis_status=SUCCESS,
                    reviews__sentiment__sentiment_label="negative",
                ),
                distinct=True,
            ),
            neutral_reviews=Count(
                "reviews__sentiment",
                filter=Q(
                    reviews__sentiment__analysis_status=SUCCESS,
                    reviews__sentiment__sentiment_label="neutral",
                ),
                distinct=True,
            ),
        )
        .order_by("-total_reviews")
    )


def calculate_perfume_scores():
    """Calculate ranking scores for all published perfumes.

    Returns:
        A list of dicts, one per published perfume, ordered by final score
        (highest first). Each dict contains:

            perfume                — Perfume instance
            rank                   — int or None (None if excluded)
            total_reviews          — int
            average_overall_rating — float or None
            overall_score          — float (0–100) or None
            analyzed_reviews       — int
            positive_reviews       — int
            negative_reviews       — int
            neutral_reviews        — int
            sentiment_score        — float (0–100) or None
            confidence             — float (0–100)
            longevity_score        — float (0–100) or None
            projection_score       — float (0–100) or None
            value_score            — float (0–100) or None
            final_score            — float (0–100) or None
            ranking_available      — bool (True if >= min reviews AND has sentiment)
            insufficient_reason    — str or None
    """
    perfumes = _perfume_review_stats()
    results = []

    for perfume in perfumes:
        total = perfume.total_reviews or 0
        avg_rating = perfume.average_overall_rating
        analyzed = perfume.analyzed_reviews or 0
        positive = perfume.positive_reviews or 0
        negative = perfume.negative_reviews or 0
        neutral = perfume.neutral_reviews or 0

        # Determine if ranking is available.
        # Need at least MIN_REVIEWS_FOR_RANKING submissions AND at least one
        # successfully analysed sentiment record for sentiment data.
        has_min_reviews = total >= MIN_REVIEWS_FOR_RANKING
        has_sentiment = analyzed > 0
        ranking_available = has_min_reviews and has_sentiment

        # Component calculations.
        if avg_rating is not None:
            overall_score = (avg_rating / 5.0) * 100.0
        else:
            overall_score = None

        if perfume.avg_longevity is not None:
            longevity_score = (perfume.avg_longevity / 5.0) * 100.0
        else:
            longevity_score = None

        if perfume.avg_projection is not None:
            projection_score = (perfume.avg_projection / 5.0) * 100.0
        else:
            projection_score = None

        if perfume.avg_value is not None:
            value_score = (perfume.avg_value / 5.0) * 100.0
        else:
            value_score = None

        if analyzed > 0:
            sentiment_score = (positive / analyzed) * 100.0
        else:
            sentiment_score = None

        confidence = (min(total, CONFIDENCE_DENOMINATOR) / CONFIDENCE_DENOMINATOR) * 100.0

        # Final weighted score (only when ranking is available).
        if ranking_available:
            final_score = (
                (overall_score * WEIGHT_OVERALL)
                + (sentiment_score * WEIGHT_SENTIMENT)
                + (confidence * WEIGHT_CONFIDENCE)
                + (longevity_score * WEIGHT_LONGEVITY)
                + (projection_score * WEIGHT_PROJECTION)
                + (value_score * WEIGHT_VALUE)
            )
        else:
            final_score = None

        # Determine insufficient-data reason.
        if total < MIN_REVIEWS_FOR_RANKING:
            insufficient_reason = (
                f"Needs {MIN_REVIEWS_FOR_RANKING - total} more "
                f"submission{'s' if MIN_REVIEWS_FOR_RANKING - total != 1 else ''} "
                f"for reliable ranking."
            )
        elif not has_sentiment:
            insufficient_reason = (
                "No successfully analyzed sentiment data yet. "
                "Run sentiment analysis to enable ranking."
            )
        else:
            insufficient_reason = None

        results.append(
            {
                "perfume": perfume,
                "total_reviews": total,
                "average_overall_rating": round(avg_rating, 2) if avg_rating is not None else None,
                "overall_score": round(overall_score, 2) if overall_score is not None else None,
                "analyzed_reviews": analyzed,
                "positive_reviews": positive,
                "negative_reviews": negative,
                "neutral_reviews": neutral,
                "sentiment_score": round(sentiment_score, 1) if sentiment_score is not None else None,
                "confidence": round(confidence, 1),
                "longevity_score": round(longevity_score, 2) if longevity_score is not None else None,
                "projection_score": round(projection_score, 2) if projection_score is not None else None,
                "value_score": round(value_score, 2) if value_score is not None else None,
                "final_score": round(final_score, 2) if final_score is not None else None,
                "ranking_available": ranking_available,
                "insufficient_reason": insufficient_reason,
            }
        )

    # Sort: perfumes with available ranking first (by final score desc),
    # then perfumes with insufficient data (by total reviews desc).
    # Tie-break: higher average rating, then higher review count.
    available = [r for r in results if r["ranking_available"]]
    unavailable = [r for r in results if not r["ranking_available"]]

    available.sort(
        key=lambda r: (
            r["final_score"] if r["final_score"] is not None else -1,
            r["average_overall_rating"] if r["average_overall_rating"] is not None else -1,
            r["total_reviews"],
        ),
        reverse=True,
    )

    unavailable.sort(
        key=lambda r: (
            r["total_reviews"],
            r["average_overall_rating"] if r["average_overall_rating"] is not None else -1,
        ),
        reverse=True,
    )

    sorted_results = available + unavailable

    # Assign ranks only to perfumes with available ranking.
    for rank, result in enumerate(sorted_results, start=1):
        if result["ranking_available"]:
            result["rank"] = rank
        else:
            result["rank"] = None

    return sorted_results


def get_ranked_perfumes(limit=None):
    """Return perfumes eligible for reliable ranking, ordered by final score.

    Args:
        limit: Maximum number of perfumes to return (None = all).

    Returns:
        List of result dicts (see calculate_perfume_scores) for perfumes where
        ranking_available is True.
    """
    results = calculate_perfume_scores()
    ranked = [r for r in results if r["ranking_available"]]
    if limit is not None:
        ranked = ranked[:limit]
    return ranked


def get_insufficient_data_perfumes(limit=None):
    """Return perfumes that do not qualify for reliable ranking.

    Args:
        limit: Maximum number of perfumes to return (None = all).

    Returns:
        List of result dicts for perfumes where ranking_available is False.
    """
    results = calculate_perfume_scores()
    insufficient = [r for r in results if not r["ranking_available"]]
    if limit is not None:
        insufficient = insufficient[:limit]
    return insufficient


def get_perfume_ranking(perfume):
    """Return ranking info for a single perfume.

    Args:
        perfume: A Perfume instance.

    Returns:
        A result dict (see calculate_perfume_scores) for the given perfume,
        or None if the perfume is not published.
    """
    results = calculate_perfume_scores()
    for result in results:
        if result["perfume"].pk == perfume.pk:
            return result
    return None
