"""Tests for the accounts app."""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User


class AccountAccessTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_login_page_renders(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_register_redirects_to_login(self):
        response = self.client.get(reverse("accounts:register"))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("accounts:login"))

    def test_staff_can_login(self):
        User.objects.create_superuser("staff", "s@example.com", "pass1234")
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "staff", "password": "pass1234"},
        )
        self.assertEqual(response.status_code, 302)
