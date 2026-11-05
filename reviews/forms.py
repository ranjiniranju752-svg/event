"""Visitor review form for ScentScope perfumes."""

from django import forms

from perfumes.models import Perfume

from .models import Review

RATING_CHOICES = [
    (value, f"{value} star{'s' if value != 1 else ''}") for value in range(1, 6)
]


class ReviewForm(forms.Form):
    """Visitor review form.

    Submitted and analysed by the backend flow in views.submit_review. All
    fields and validation rules live here so the browser and server agree.
    """

    reviewer_name = forms.CharField(
        max_length=100,
        label="Your name",
        widget=forms.TextInput(
            attrs={
                "placeholder": "e.g. Maya Rao",
                "autocomplete": "name",
                "class": "form-control",
            }
        ),
    )
    reviewer_email = forms.EmailField(
        label="Email address",
        help_text="Used only to send your Tracking ID. Never shown publicly.",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "you@example.com",
                "autocomplete": "email",
                "class": "form-control",
            }
        ),
    )
    overall_rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        label="Overall experience",
        widget=forms.RadioSelect(attrs={"class": "star-input"}),
    )
    longevity_rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        label="Longevity",
        help_text="How long the scent lasts on your skin.",
        widget=forms.RadioSelect(attrs={"class": "star-input"}),
    )
    projection_rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        label="Projection",
        help_text="How far the scent travels from you.",
        widget=forms.RadioSelect(attrs={"class": "star-input"}),
    )
    sillage_rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        label="Sillage",
        help_text="The scent trail it leaves behind.",
        widget=forms.RadioSelect(attrs={"class": "star-input"}),
    )
    fragrance_rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        label="Fragrance quality",
        help_text="How much you enjoy the scent itself.",
        widget=forms.RadioSelect(attrs={"class": "star-input"}),
    )
    value_for_money_rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        label="Value for money",
        help_text="Is it worth the price?",
        widget=forms.RadioSelect(attrs={"class": "star-input"}),
    )
    season_suitability = forms.ChoiceField(
        choices=Review.SeasonSuitability.choices,
        label="Best season",
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    occasion_suitability = forms.ChoiceField(
        choices=Review.OccasionSuitability.choices,
        label="Best occasion",
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    written_review = forms.CharField(
        label="Your written review",
        min_length=10,
        max_length=2000,
        widget=forms.Textarea(
            attrs={
                "rows": 6,
                "placeholder": "What did you think of the scent? Mention the "
                "notes, longevity, projection, occasion…",
                "class": "form-control",
                "data-counter-target": "message-counter",
            }
        ),
    )
    # Honeypot: real visitors never see or fill this field.
    website = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={"tabindex": "-1", "autocomplete": "off"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["season_suitability"].empty_label = "Any season"
        self.fields["occasion_suitability"].empty_label = "Any occasion"

    def clean_written_review(self):
        message = self.cleaned_data["written_review"].strip()
        if len(message) < 10:
            raise forms.ValidationError("Please write at least 10 characters.")
        return message

    def clean(self):
        cleaned = super().clean()
        # Convert rating strings to ints for the model layer.
        for field in (
            "overall_rating",
            "longevity_rating",
            "projection_rating",
            "sillage_rating",
            "fragrance_rating",
            "value_for_money_rating",
        ):
            if field in cleaned and cleaned[field] not in (None, ""):
                try:
                    cleaned[field] = int(cleaned[field])
                except (TypeError, ValueError):
                    cleaned[field] = None
        return cleaned
