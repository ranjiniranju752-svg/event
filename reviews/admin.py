from django.contrib import admin

from .models import Review, ReviewSentiment


class ReviewSentimentInline(admin.StackedInline):
    model = ReviewSentiment
    extra = 0


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        "tracking_id",
        "perfume",
        "reviewer_name",
        "overall_rating",
        "is_approved",
        "created_at",
    ]
    list_filter = ["is_approved", "overall_rating", "created_at", "perfume"]
    search_fields = ["tracking_id", "reviewer_name", "written_review"]
    readonly_fields = ["tracking_id", "created_at", "updated_at"]
    inlines = [ReviewSentimentInline]


@admin.register(ReviewSentiment)
class ReviewSentimentAdmin(admin.ModelAdmin):
    list_display = [
        "review",
        "sentiment_label",
        "sentiment_score",
        "rating_sentiment",
        "is_mismatch",
        "analysis_status",
        "analyzed_at",
    ]
    list_filter = ["analysis_status", "sentiment_label", "is_mismatch"]
    search_fields = ["review__tracking_id"]
    readonly_fields = ["analyzed_at"]
