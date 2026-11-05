"""Management command to retry failed review sentiment analyses."""

from django.core.management.base import BaseCommand

from reviews.services.sentiment import retry_failed_analyses


class Command(BaseCommand):
    help = "Retry sentiment analysis for reviews whose analysis previously failed."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of failed analyses to retry.",
        )

    def handle(self, *args, **options):
        processed, succeeded, failed = retry_failed_analyses(limit=options["limit"])
        self.stdout.write(
            f"Retried {processed} failed sentiment analysis(es): "
            f"{succeeded} succeeded, {failed} failed."
        )
