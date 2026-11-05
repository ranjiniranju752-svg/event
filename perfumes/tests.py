"""Tests for the perfumes app."""

from io import BytesIO

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from .models import Perfume, PerfumeBrand, FragranceFamily


def make_uploaded_image(name="test.jpg"):
    buffer = BytesIO()
    Image.new("RGB", (200, 300), (200, 200, 200)).save(buffer, format="JPEG")
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type="image/jpeg")


class PerfumeModelTests(TestCase):
    def setUp(self):
        self.brand = PerfumeBrand.objects.create(
            name="Maison Test", country="France", is_active=True
        )
        self.family = FragranceFamily.objects.create(
            name="Floral", is_active=True
        )

    def test_perfume_creation_and_slug(self):
        perfume = Perfume.objects.create(
            perfume_name="Test Eau de Parfum",
            brand=self.brand,
            fragrance_family=self.family,
            description="A test fragrance.",
            top_notes="Bergamot, Lemon",
            middle_notes="Jasmine, Rose",
            base_notes="Vanilla, Musk",
            concentration="edp",
            gender_category="unisex",
            launch_year=2020,
            price="120.00",
            volume_ml=100,
            image=make_uploaded_image(),
        )
        self.assertEqual(perfume.slug, "test-eau-de-parfum")
        self.assertEqual(str(perfume), "Test Eau de Parfum")
        self.assertEqual(perfume.get_absolute_url(), f"/perfumes/{perfume.slug}/")
        self.assertEqual(len(perfume.notes_list["top"]), 2)
        self.assertIn("Bergamot", perfume.notes_list["top"])

    def test_slug_uniqueness(self):
        Perfume.objects.create(
            perfume_name="Same Name",
            brand=self.brand,
            fragrance_family=self.family,
            description="First.",
            top_notes="A", middle_notes="B", base_notes="C",
            concentration="edt", gender_category="unisex",
            price="50.00", volume_ml=50,
            image=make_uploaded_image("first.jpg"),
        )
        duplicate = Perfume.objects.create(
            perfume_name="Same Name",
            brand=self.brand,
            fragrance_family=self.family,
            description="Second.",
            top_notes="A", middle_notes="B", base_notes="C",
            concentration="edt", gender_category="unisex",
            price="50.00", volume_ml=50,
            image=make_uploaded_image("second.jpg"),
        )
        self.assertEqual(duplicate.slug, "same-name-2")

    def test_published_filter(self):
        Perfume.objects.create(
            perfume_name="Published", brand=self.brand,
            fragrance_family=self.family, description="P.", top_notes="A",
            middle_notes="B", base_notes="C", concentration="edt",
            gender_category="unisex", price="50.00", volume_ml=50,
            is_published=True, image=make_uploaded_image("pub.jpg"),
        )
        Perfume.objects.create(
            perfume_name="Unpublished", brand=self.brand,
            fragrance_family=self.family, description="U.", top_notes="A",
            middle_notes="B", base_notes="C", concentration="edt",
            gender_category="unisex", price="50.00", volume_ml=50,
            is_published=False, image=make_uploaded_image("unpub.jpg"),
        )
        self.assertEqual(Perfume.objects.filter(is_published=True).count(), 1)


class PerfumeViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username="staff", email="staff@example.com", password="pass1234"
        )
        self.brand = PerfumeBrand.objects.create(name="Test Brand")
        self.family = FragranceFamily.objects.create(name="Woody")
        self.perfume = Perfume.objects.create(
            perfume_name="Woody Test",
            brand=self.brand,
            fragrance_family=self.family,
            description="A woody test fragrance.",
            top_notes="Cedar",
            middle_notes="Vetiver",
            base_notes="Musk",
            concentration="edp",
            gender_category="men",
            price="90.00",
            volume_ml=100,
            is_published=True,
            image=make_uploaded_image(),
        )

    def test_home_renders(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_perfume_list_renders(self):
        response = self.client.get(reverse("perfumes:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Woody Test")

    def test_perfume_detail_renders(self):
        response = self.client.get(
            reverse("perfumes:detail", kwargs={"slug": self.perfume.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Woody Test")
        self.assertContains(response, "Cedar")

    def test_search_filters_results(self):
        response = self.client.get(reverse("perfumes:list") + "?q=woody")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Woody Test")

    def test_family_filter(self):
        response = self.client.get(
            reverse("perfumes:list") + f"?family={self.family.slug}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Woody Test")

    def test_staff_pages_require_login(self):
        response = self.client.get(reverse("perfumes_staff:perfume_list_staff"))
        self.assertEqual(response.status_code, 302)

    def test_staff_can_access_after_login(self):
        self.client.login(username="staff", password="pass1234")
        response = self.client.get(reverse("perfumes_staff:perfume_list_staff"))
        self.assertEqual(response.status_code, 200)

    def test_staff_add_perfume(self):
        self.client.login(username="staff", password="pass1234")
        response = self.client.post(
            reverse("perfumes_staff:perfume_add"),
            {
                "perfume_name": "New Fragrance",
                "brand": self.brand.pk,
                "fragrance_family": self.family.pk,
                "description": "New scent.",
                "top_notes": "A",
                "middle_notes": "B",
                "base_notes": "C",
                "concentration": "edt",
                "gender_category": "unisex",
                "launch_year": 2021,
                "price": "75.00",
                "volume_ml": 50,
                "longevity_category": "moderate",
                "sillage_category": "moderate",
                "availability_status": "in_stock",
                "is_published": True,
                "image": make_uploaded_image(),
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Perfume.objects.filter(perfume_name="New Fragrance").exists())
