"""Public and staff views for the ScentScope perfume catalogue."""

from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from analytics.services import (
    aspect_leaderboard,
    rating_breakdown,
    sentiment_breakdown,
)
from analytics.services.ranking import get_perfume_ranking
from reviews.models import Review

from .forms import PerfumeForm
from .models import FragranceFamily, Perfume
from .services import perfume_cards


def home(request):
    """Landing page: featured perfume, newest arrivals and top-rated titles."""
    perfumes = perfume_cards().filter(is_published=True)

    featured = (
        perfumes.filter(review_count__gt=0)
        .order_by("-average_rating", "-review_count")
        .first()
        or perfumes.order_by("-created_at").first()
    )

    reviews = Review.objects.aggregate(total=Count("id"), avg=Avg("overall_rating"))

    return render(
        request,
        "home.html",
        {
            "featured": featured,
            "latest_perfumes": perfumes.order_by("-created_at")[:6],
            "top_perfumes": perfumes.filter(review_count__gt=0).order_by(
                "-average_rating", "-review_count"
            )[:3],
            "families": FragranceFamily.objects.filter(is_active=True),
            "stats": {
                "perfumes": Perfume.objects.count(),
                "reviews": reviews["total"] or 0,
                "average": round(reviews["avg"] or 0, 1),
            },
        },
    )


def perfume_list(request):
    """Browse published perfumes with search, filters and pagination."""
    queryset = perfume_cards().filter(is_published=True).order_by("-created_at")

    query = (request.GET.get("q") or "").strip()
    family = (request.GET.get("family") or "").strip()
    concentration = (request.GET.get("concentration") or "").strip()
    gender = (request.GET.get("gender") or "").strip()
    price_max = (request.GET.get("price_max") or "").strip()
    sort = (request.GET.get("sort") or "newest").strip()

    if query:
        queryset = queryset.filter(
            Q(perfume_name__icontains=query)
            | Q(brand__name__icontains=query)
            | Q(top_notes__icontains=query)
            | Q(middle_notes__icontains=query)
            | Q(base_notes__icontains=query)
            | Q(description__icontains=query)
        )
    if family:
        queryset = queryset.filter(fragrance_family__slug=family)
    if concentration in dict(Perfume.Concentration.choices):
        queryset = queryset.filter(concentration=concentration)
    if gender in dict(Perfume.GenderCategory.choices):
        queryset = queryset.filter(gender_category=gender)
    if price_max:
        try:
            queryset = queryset.filter(price__lte=float(price_max))
        except ValueError:
            pass

    if sort == "rating":
        queryset = queryset.filter(review_count__gt=0).order_by(
            "-average_rating", "-review_count"
        )
    elif sort == "price-low":
        queryset = queryset.order_by("price")
    elif sort == "price-high":
        queryset = queryset.order_by("-price")
    else:
        queryset = queryset.order_by("-created_at")

    paginator = Paginator(queryset, 9)
    page_obj = paginator.get_page(request.GET.get("page"))

    params = request.GET.copy()
    params.pop("page", None)

    return render(
        request,
        "perfumes/list.html",
        {
            "page_obj": page_obj,
            "perfumes": page_obj.object_list,
            "families": FragranceFamily.objects.filter(is_active=True),
            "concentrations": Perfume.Concentration.choices,
            "genders": Perfume.GenderCategory.choices,
            "active_family": family,
            "active_concentration": concentration,
            "active_gender": gender,
            "active_price_max": price_max,
            "active_sort": sort,
            "query": query,
            "query_suffix": params.urlencode(),
        },
    )


def perfume_detail(request, slug):
    """Public perfume page with rating summary and recent customer reviews."""
    perfume = get_object_or_404(perfume_cards().filter(is_published=True), slug=slug)
    review_queryset = (
        perfume.reviews.filter(is_approved=True)
        .select_related("sentiment")
        .order_by("-created_at")
    )

    return render(
        request,
        "perfumes/detail.html",
        {
            "perfume": perfume,
            "gallery_images": perfume.gallery_images.all(),
            "recent_reviews": review_queryset[:6],
            "review_total": review_queryset.count(),
            "rating_counts": rating_breakdown(review_queryset),
            "sentiment": sentiment_breakdown(review_queryset),
            "aspects": aspect_leaderboard(review_queryset),
            "perfume_ranking": get_perfume_ranking(perfume),
        },
    )


@staff_member_required
def perfume_list_staff(request):
    """Staff view: list all perfumes with publish status."""
    perfumes = Perfume.objects.all().order_by("-created_at")
    return render(
        request,
        "staff/perfume_list.html",
        {"perfumes": perfumes},
    )


@staff_member_required
def perfume_add(request):
    """Staff view: add a new perfume."""
    if request.method == "POST":
        form = PerfumeForm(request.POST, request.FILES)
        if form.is_valid():
            perfume = form.save()
            return redirect("perfumes_staff:perfume_list_staff")
    else:
        form = PerfumeForm()
    return render(
        request,
        "staff/perfume_form.html",
        {"form": form, "action": "Add"},
    )


@staff_member_required
def perfume_edit(request, pk):
    """Staff view: edit an existing perfume."""
    perfume = get_object_or_404(Perfume, pk=pk)
    if request.method == "POST":
        form = PerfumeForm(request.POST, request.FILES, instance=perfume)
        if form.is_valid():
            form.save()
            return redirect("perfumes_staff:perfume_list_staff")
    else:
        form = PerfumeForm(instance=perfume)
    return render(
        request,
        "staff/perfume_form.html",
        {"form": form, "perfume": perfume, "action": "Edit"},
    )


@staff_member_required
def perfume_delete(request, pk):
    """Staff view: delete a perfume with confirmation."""
    perfume = get_object_or_404(Perfume, pk=pk)
    review_count = perfume.reviews.count()
    if request.method == "POST":
        perfume.delete()
        return redirect("perfumes_staff:perfume_list_staff")
    return render(
        request,
        "staff/perfume_confirm_delete.html",
        {"perfume": perfume, "review_count": review_count},
    )


@staff_member_required
def perfume_toggle_publish(request, pk):
    """Staff view: toggle a perfume's published status."""
    perfume = get_object_or_404(Perfume, pk=pk)
    perfume.is_published = not perfume.is_published
    perfume.save()
    return redirect("perfumes_staff:perfume_list_staff")
