"""Validation helpers for uploaded perfume images and launch years."""

import datetime

from django.core.exceptions import ValidationError

MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5 MB


def validate_perfume_image_size(image):
    """Reject perfume image files larger than 5 MB."""
    if image.size > MAX_IMAGE_SIZE:
        raise ValidationError("Image must be 5 MB or smaller.")


def validate_not_future_year(value):
    """Launch years cannot be in the future."""
    current_year = datetime.date.today().year
    if value and value > current_year:
        raise ValidationError(f"Launch year cannot be in the future ({current_year}).")
