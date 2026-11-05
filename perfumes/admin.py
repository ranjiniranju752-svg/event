from django.contrib import admin

from .models import FragranceFamily, Perfume, PerfumeBrand, PerfumeImage


@admin.register(PerfumeBrand)
class PerfumeBrandAdmin(admin.ModelAdmin):
    list_display = ["name", "country", "founded_year", "is_active", "created_at"]
    list_filter = ["is_active", "country"]
    search_fields = ["name", "country"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(FragranceFamily)
class FragranceFamilyAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Perfume)
class PerfumeAdmin(admin.ModelAdmin):
    list_display = [
        "perfume_name",
        "brand",
        "fragrance_family",
        "concentration",
        "gender_category",
        "price",
        "is_published",
        "created_at",
    ]
    list_filter = [
        "is_published",
        "concentration",
        "gender_category",
        "fragrance_family",
        "brand",
        "availability_status",
    ]
    search_fields = ["perfume_name", "brand__name", "top_notes", "middle_notes", "base_notes"]
    prepopulated_fields = {"slug": ("perfume_name",)}
    readonly_fields = ["created_at", "updated_at"]


@admin.register(PerfumeImage)
class PerfumeImageAdmin(admin.ModelAdmin):
    list_display = ["perfume", "is_primary", "uploaded_at"]
    list_filter = ["is_primary"]
    search_fields = ["perfume__perfume_name"]
