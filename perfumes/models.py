"""Database models for the ScentScope perfume catalogue."""

from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from .validators import validate_perfume_image_size, validate_not_future_year


class PerfumeBrand(models.Model):
    """A perfume house or brand (e.g. Chanel, Dior, Jo Malone)."""

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    country = models.CharField(max_length=100, blank=True, help_text="Country of origin.")
    founded_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[validate_not_future_year],
        help_text="Year the brand was founded.",
    )
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "perfume brand"
        verbose_name_plural = "perfume brands"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:100] or "brand"
            slug = base
            counter = 2
            while PerfumeBrand.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("perfumes:list") + f"?brand={self.slug}"


class FragranceFamily(models.Model):
    """Olfactory family a perfume belongs to (e.g. Floral, Woody, Oriental)."""

    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "fragrance family"
        verbose_name_plural = "fragrance families"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:90] or "family"
            slug = base
            counter = 2
            while FragranceFamily.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("perfumes:list") + f"?family={self.slug}"


class Perfume(models.Model):
    """A perfume that visitors can browse and review."""

    class Concentration(models.TextChoices):
        EDT = "edt", "Eau de Toilette (EDT)"
        EDP = "edp", "Eau de Parfum (EDP)"
        EDC = "edc", "Eau de Cologne (EDC)"
        PARFUM = "parfum", "Parfum / Extrait"

    class GenderCategory(models.TextChoices):
        UNISEX = "unisex", "Unisex"
        MEN = "men", "For Men"
        WOMEN = "women", "For Women"

    class LongevityCategory(models.TextChoices):
        SHORT = "short", "Short (1-4 hours)"
        MODERATE = "moderate", "Moderate (4-8 hours)"
        LONG = "long", "Long (8-12 hours)"
        VERY_LONG = "very_long", "Very Long (12+ hours)"

    class SillageCategory(models.TextChoices):
        SOFT = "soft", "Soft (skin-close)"
        MODERATE = "moderate", "Moderate (noticeable)"
        STRONG = "strong", "Strong (strong trail)"
        INTENSE = "intense", "Intense (powerful trail)"

    class AvailabilityStatus(models.TextChoices):
        IN_STOCK = "in_stock", "In Stock"
        LIMITED = "limited", "Limited Availability"
        DISCONTINUED = "discontinued", "Discontinued"

    perfume_name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    brand = models.ForeignKey(
        PerfumeBrand,
        on_delete=models.PROTECT,
        related_name="perfumes",
        help_text="Brand or perfume house.",
    )
    description = models.TextField(help_text="Perfume description and story.")
    fragrance_family = models.ForeignKey(
        FragranceFamily,
        on_delete=models.PROTECT,
        related_name="perfumes",
        help_text="Primary olfactory family.",
    )
    top_notes = models.CharField(
        max_length=200, help_text="Comma-separated top notes (first impression)."
    )
    middle_notes = models.CharField(
        max_length=200, help_text="Comma-separated middle / heart notes."
    )
    base_notes = models.CharField(
        max_length=200, help_text="Comma-separated base notes (dry-down)."
    )
    concentration = models.CharField(
        max_length=10, choices=Concentration.choices, default=Concentration.EDP
    )
    gender_category = models.CharField(
        max_length=10, choices=GenderCategory.choices, default=GenderCategory.UNISEX
    )
    launch_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[validate_not_future_year],
        help_text="Year the perfume was launched.",
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Retail price in local currency."
    )
    volume_ml = models.PositiveSmallIntegerField(help_text="Bottle size in millilitres.")
    image = models.ImageField(
        upload_to="perfumes/",
        blank=True,
        validators=[
            FileExtensionValidator(["jpg", "jpeg", "png", "webp"]),
            validate_perfume_image_size,
        ],
        help_text="Main perfume bottle image.",
    )
    longevity_category = models.CharField(
        max_length=15,
        choices=LongevityCategory.choices,
        default=LongevityCategory.MODERATE,
        help_text="How long the scent lasts on skin.",
    )
    sillage_category = models.CharField(
        max_length=15,
        choices=SillageCategory.choices,
        default=SillageCategory.MODERATE,
        help_text="How far the scent projects from the wearer.",
    )
    availability_status = models.CharField(
        max_length=20,
        choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.IN_STOCK,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(
        default=False,
        help_text="Only published perfumes are visible to public visitors.",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["brand", "is_published"]),
            models.Index(fields=["fragrance_family", "is_published"]),
            models.Index(fields=["is_published", "-created_at"]),
        ]

    def __str__(self):
        return self.perfume_name

    def save(self, *args, **kwargs):
        """Create a unique slug from the perfume name when one is not supplied."""
        if not self.slug:
            base = slugify(self.perfume_name)[:200] or "perfume"
            slug = base
            counter = 2
            while Perfume.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("perfumes:detail", kwargs={"slug": self.slug})

    @property
    def notes_list(self):
        """Return each note block as a list of stripped strings."""
        return {
            "top": [note.strip() for note in self.top_notes.split(",") if note.strip()],
            "middle": [
                note.strip() for note in self.middle_notes.split(",") if note.strip()
            ],
            "base": [note.strip() for note in self.base_notes.split(",") if note.strip()],
        }


class PerfumeImage(models.Model):
    """Additional gallery image for a perfume."""

    perfume = models.ForeignKey(
        Perfume, on_delete=models.CASCADE, related_name="gallery_images"
    )
    image = models.ImageField(
        upload_to="perfumes/gallery/",
        blank=True,
        validators=[
            FileExtensionValidator(["jpg", "jpeg", "png", "webp"]),
            validate_perfume_image_size,
        ],
    )
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_primary", "uploaded_at"]

    def __str__(self):
        return f"Image for {self.perfume.perfume_name}"
