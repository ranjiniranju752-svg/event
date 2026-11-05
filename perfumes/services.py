"""Read-only queries for perfume pages."""

from django.db.models import Avg, Count

from .models import Perfume


def perfume_cards():
    """Perfumes annotated with rating information for cards and detail pages."""
    return Perfume.objects.annotate(
        average_rating=Avg("reviews__overall_rating"),
        review_count=Count("reviews", distinct=True),
        avg_longevity=Avg("reviews__longevity_rating"),
        avg_projection=Avg("reviews__projection_rating"),
        avg_value=Avg("reviews__value_for_money_rating"),
    )
