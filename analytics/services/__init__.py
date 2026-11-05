"""All analytics queries live here.

Views stay short: they call these functions and return templates or JSON.
Every number is calculated from the database — nothing is hardcoded.
"""

from collections import Counter
from datetime import timedelta

from django.db.models import Avg, Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from perfumes.models import Perfume
from reviews.models import Review, ReviewSentiment

from . import ranking

SENTIMENTS = ("positive", "neutral", "negative")
SUCCESS = ReviewSentiment.Status.SUCCESS


def sentiment_breakdown(review_queryset=None):
    """Counts, percentages and total of successful analyses."""
    queryset = ReviewSentiment.objects.filter(analysis_status=SUCCESS)
    if review_queryset is not None:
        queryset = queryset.filter(review__in=review_queryset)

    counts = {key: 0 for key in SENTIMENTS}
    for row in queryset.values("sentiment_label").annotate(n=Count("id")):
        if row["sentiment_label"] in counts:
            counts[row["sentiment_label"]] = row["n"]

    total = sum(counts.values())
    percentages = {
        key: round((value / total) * 100, 1) if total else 0.0
        for key, value in counts.items()
    }
    return {
        "counts": counts,
        "percentages": percentages,
        "total": total,
    }


def aspect_leaderboard(review_queryset=None, limit=6):
    """Most mentioned positive keywords and negative complaints."""
    queryset = ReviewSentiment.objects.filter(analysis_status=SUCCESS)
    if review_queryset is not None:
        queryset = queryset.filter(review__in=review_queryset)

    positive = Counter()
    negative = Counter()
    for positive_keywords, negative_keywords in queryset.values_list(
        "positive_keywords", "negative_keywords"
    ):
        positive.update(positive_keywords or [])
        negative.update(negative_keywords or [])

    return {
        "positive": positive.most_common(limit),
        "negative": negative.most_common(limit),
    }


def rating_breakdown(review_queryset):
    """How many 1–5 overall star ratings a perfume received."""
    counts = {value: 0 for value in range(1, 6)}
    for row in review_queryset.values("overall_rating").annotate(n=Count("id")):
        counts[row["overall_rating"]] = row["n"]
    return counts


def overall_stats():
    reviews = Review.objects.aggregate(total=Count("id"), avg=Avg("overall_rating"))
    return {
        "total_perfumes": Perfume.objects.count(),
        "total_reviews": reviews["total"] or 0,
        "average_rating": round(reviews["avg"] or 0, 2),
    }


def dashboard_context():
    stats = overall_stats()
    sentiment = sentiment_breakdown()
    recent = (
        Review.objects.select_related("perfume", "sentiment")
        .order_by("-created_at")[:8]
    )
    top_perfumes = (
        Perfume.objects.annotate(
            average_rating=Avg("reviews__overall_rating"),
            review_count=Count("reviews", distinct=True),
        )
        .filter(review_count__gt=0)
        .order_by("-average_rating", "-review_count")[:5]
    )
    mismatches = ReviewSentiment.objects.filter(
        analysis_status=SUCCESS, is_mismatch=True
    ).count()

    return {
        **stats,
        "sentiment": sentiment,
        "recent_reviews": recent,
        "top_perfumes": top_perfumes,
        "mismatch_count": mismatches,
        "today": timezone.localdate(),
    }


def perfume_ratings_chart():
    rows = (
        Perfume.objects.annotate(
            average_rating=Avg("reviews__overall_rating"),
            review_count=Count("reviews", distinct=True),
        )
        .filter(review_count__gt=0)
        .order_by("-average_rating")[:10]
    )
    return {
        "labels": [row.perfume_name for row in rows],
        "ratings": [round(float(row.average_rating), 2) for row in rows],
        "counts": [row.review_count for row in rows],
    }


def sentiment_by_perfume_chart():
    rows = (
        Review.objects.values("perfume__perfume_name", "sentiment__sentiment_label")
        .filter(sentiment__analysis_status=SUCCESS)
        .annotate(n=Count("id"))
        .order_by("perfume__perfume_name")
    )

    perfumes = []
    series = {key: [] for key in SENTIMENTS}
    for row in rows:
        name = row["perfume__perfume_name"]
        if name not in perfumes:
            perfumes.append(name)
            for key in SENTIMENTS:
                series[key].append(0)
        index = perfumes.index(name)
        label = row["sentiment__sentiment_label"]
        if label in series:
            series[label][index] = row["n"]

    return {"labels": perfumes, **series}


def review_trend_chart(days=30):
    """Daily review volume with positive and negative lines."""
    end = timezone.localdate()
    start = end - timedelta(days=days - 1)

    rows = (
        Review.objects.filter(created_at__date__gte=start)
        .values("created_at__date", "sentiment__sentiment_label")
        .annotate(n=Count("id"))
    )

    by_day = {}
    for row in rows:
        day = row["created_at__date"].isoformat()
        entry = by_day.setdefault(day, {"total": 0, "positive": 0, "negative": 0})
        entry["total"] += row["n"]
        sentiment = row["sentiment__sentiment_label"]
        if sentiment in ("positive", "negative"):
            entry[sentiment] += row["n"]

    labels = []
    totals = []
    positive = []
    negative = []
    for offset in range(days):
        day = (start + timedelta(days=offset)).isoformat()
        entry = by_day.get(day, {"total": 0, "positive": 0, "negative": 0})
        labels.append(day)
        totals.append(entry["total"])
        positive.append(entry["positive"])
        negative.append(entry["negative"])

    return {
        "labels": labels,
        "total": totals,
        "positive": positive,
        "negative": negative,
    }
