import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Create (or ensure) a Django superuser from environment variables. "
        "No-op unless DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_PASSWORD are set."
    )

    def handle(self, *args, **options):
        username = os.getenv("DJANGO_SUPERUSER_USERNAME", "").strip()
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "").strip()
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "")

        if not username or not password:
            self.stdout.write(
                "ensure_superuser: skipped (set DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_PASSWORD)"
            )
            return

        set_password = os.getenv(
            "DJANGO_SUPERUSER_SET_PASSWORD", ""
        ).strip().lower() in (
            "1",
            "true",
            "yes",
        )

        User = get_user_model()

        defaults = {}
        if email:
            defaults["email"] = email

        user, created = User.objects.get_or_create(username=username, defaults=defaults)

        changed = False
        if created:
            user.is_staff = True
            user.is_superuser = True
            user.set_password(password)
            if email:
                user.email = email
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f"ensure_superuser: created '{username}'")
            )
            return

        if not user.is_staff:
            user.is_staff = True
            changed = True

        if not user.is_superuser:
            user.is_superuser = True
            changed = True

        if email and user.email != email:
            user.email = email
            changed = True

        if set_password:
            user.set_password(password)
            changed = True

        if changed:
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f"ensure_superuser: updated '{username}'")
            )
        else:
            self.stdout.write(f"ensure_superuser: ok ('{username}' already exists)")
