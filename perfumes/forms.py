from django import forms

from .models import Perfume


class PerfumeForm(forms.ModelForm):
    """Form for adding and editing perfumes (staff only)."""

    class Meta:
        model = Perfume
        fields = [
            "perfume_name",
            "brand",
            "description",
            "image",
            "fragrance_family",
            "top_notes",
            "middle_notes",
            "base_notes",
            "concentration",
            "gender_category",
            "launch_year",
            "price",
            "volume_ml",
            "longevity_category",
            "sillage_category",
            "availability_status",
            "is_published",
        ]
        widgets = {
            "perfume_name": forms.TextInput(attrs={"class": "form-control"}),
            "brand": forms.Select(attrs={"class": "form-control"}),
            "description": forms.Textarea(
                attrs={"rows": 4, "class": "form-control"}
            ),
            "fragrance_family": forms.Select(attrs={"class": "form-control"}),
            "top_notes": forms.TextInput(attrs={"class": "form-control"}),
            "middle_notes": forms.TextInput(attrs={"class": "form-control"}),
            "base_notes": forms.TextInput(attrs={"class": "form-control"}),
            "concentration": forms.Select(attrs={"class": "form-control"}),
            "gender_category": forms.Select(attrs={"class": "form-control"}),
            "launch_year": forms.NumberInput(
                attrs={"type": "number", "class": "form-control", "min": 1900}
            ),
            "price": forms.NumberInput(
                attrs={"type": "number", "class": "form-control", "step": "0.01", "min": "0"}
            ),
            "volume_ml": forms.NumberInput(
                attrs={"type": "number", "class": "form-control", "min": "1"}
            ),
            "longevity_category": forms.Select(attrs={"class": "form-control"}),
            "sillage_category": forms.Select(attrs={"class": "form-control"}),
            "availability_status": forms.Select(attrs={"class": "form-control"}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "is_published": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["brand"].queryset = self.fields["brand"].queryset.order_by("name")
        self.fields["fragrance_family"].queryset = (
            self.fields["fragrance_family"].queryset.order_by("name")
        )
        self.fields["is_published"].label = "Publish publicly"
        self.fields["is_published"].help_text = (
            "Unpublished perfumes are hidden from public visitors."
        )
        self.fields["brand"].empty_label = "Select a brand"
        self.fields["fragrance_family"].empty_label = "Select a fragrance family"
