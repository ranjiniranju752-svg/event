"""Public review submission, confirmation and tracking views."""

from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from perfumes.services import perfume_cards

from .forms import ReviewForm
from .models import Review, ReviewSentiment
from .services.sentiment import analyze_review
from .tracking import generate_unique_tracking_id


def submit_review(request, slug):
    """Review form page and submission handler.

    GET: renders the review form for a published perfume.
    POST: validates the form, saves the review with a unique tracking ID,
    creates a ReviewSentiment record, runs sentiment analysis, and redirects
    to the success page. Sentiment analysis failures never block submission.
    """
    perfume = get_object_or_404(perfume_cards().filter(is_published=True), slug=slug)

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            # Honeypot: if the hidden website field is filled, treat as spam.
            if form.cleaned_data.get("website"):
                form.add_error(None, "Submission rejected.")
                return render(
                    request,
                    "reviews/submit.html",
                    {"perfume": perfume, "form": form},
                )

            cleaned = form.cleaned_data
            with transaction.atomic():
                review = Review.objects.create(
                    perfume=perfume,
                    reviewer_name=cleaned["reviewer_name"],
                    reviewer_email=cleaned["reviewer_email"],
                    overall_rating=int(cleaned["overall_rating"]),
                    longevity_rating=int(cleaned["longevity_rating"]),
                    projection_rating=int(cleaned["projection_rating"]),
                    sillage_rating=int(cleaned["sillage_rating"]),
                    fragrance_rating=int(cleaned["fragrance_rating"]),
                    value_for_money_rating=int(cleaned["value_for_money_rating"]),
                    season_suitability=cleaned.get("season_suitability") or "",
                    occasion_suitability=cleaned.get("occasion_suitability") or "",
                    written_review=cleaned["written_review"],
                    tracking_id=generate_unique_tracking_id(),
                )
                # Create a pending analysis row. Module populates it below.
                ReviewSentiment.objects.create(
                    review=review,
                    analysis_status=ReviewSentiment.Status.PENDING,
                )
                # Run sentiment analysis immediately. Any failure is caught
                # inside analyze_review and does not roll back the review.
                analyze_review(review)

            return redirect("reviews:success", tracking_id=review.tracking_id)

    else:
        form = ReviewForm()

    return render(
        request,
        "reviews/submit.html",
        {"perfume": perfume, "form": form},
    )


def review_success(request, tracking_id):
    """Review submission confirmation page.

    Displays the tracking ID and submission summary. Never exposes the
    submitter's email address.
    """
    review = get_object_or_404(
        Review.objects.select_related("perfume", "sentiment"),
        tracking_id=tracking_id,
    )
    return render(
        request,
        "reviews/success.html",
        {"review": review},
    )


def track_review(request):
    """Tracking form page (GET only). Results handled in the same view POST."""

    review = None
    error = None

    if request.method == "POST":
        tracking_id = (request.POST.get("tracking_id") or "").strip().upper()
        if not tracking_id:
            error = "Please enter a Tracking ID."
        else:
            try:
                review = (
                    Review.objects.select_related("perfume", "sentiment")
                    .get(tracking_id=tracking_id)
                )
            except Review.DoesNotExist:
                error = "No review found for that Tracking ID."

    return render(
        request,
        "reviews/track.html",
        {"review": review, "error": error},
    )
