"""
Management command to import members from the cleaned CSV file.

This command replaces all existing members with the ones defined in
data/members_cleaned.csv.  It will NOT delete members that are
referenced by existing Contribution records (Django's PROTECT
constraint), so contributions must be cleared first when using --clear.

Usage:
    python manage.py import_members              # Add new members (skip existing)
    python manage.py import_members --clear      # Wipe members & contributions first
    python manage.py import_members --dry-run    # Preview without writing to DB
"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from finance.models import Contribution, Member

CSV_PATH = Path(__file__).resolve().parents[3] / "data" / "members_cleaned.csv"


class Command(BaseCommand):
    help = "Import community members from data/members_cleaned.csv, replacing existing members."

    # ── CLI flags ──────────────────────────────────────────────
    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete ALL existing members (and their contributions) before importing.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without writing to the database.",
        )

    # ── Main handler ──────────────────────────────────────────
    def handle(self, *args, **options):
        clear = options["clear"]
        dry_run = options["dry_run"]

        if not CSV_PATH.exists():
            raise CommandError(f"CSV file not found: {CSV_PATH}")

        # Read and validate CSV rows
        rows = self._read_csv()
        self.stdout.write(f"\n📄  Found {len(rows)} members in CSV.\n")

        if dry_run:
            self._preview(rows)
            self.stdout.write(
                self.style.WARNING("\n🚫  Dry-run mode — no changes written.\n")
            )
            return

        with transaction.atomic():
            if clear:
                self._clear_existing()

            created, skipped = self._import_members(rows)

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅  Import complete — {created} created, {skipped} skipped (already existed).\n"
            )
        )

    # ── CSV reader & validator ────────────────────────────────
    def _read_csv(self) -> list[dict]:
        """Return a list of cleaned dicts from the CSV."""
        rows: list[dict] = []

        with open(CSV_PATH, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)

            required = {"full_name", "phone"}
            if not required.issubset(reader.fieldnames or []):
                raise CommandError(
                    f"CSV is missing required columns. "
                    f"Expected at least {required}, got {reader.fieldnames}"
                )

            for lineno, row in enumerate(reader, start=2):
                full_name = (row.get("full_name") or "").strip()
                phone = (row.get("phone") or "").strip()
                notes = (row.get("notes") or "").strip()

                # ── Validation ──
                if not full_name:
                    self.stderr.write(
                        self.style.WARNING(
                            f"  ⚠  Line {lineno}: empty full_name — skipped"
                        )
                    )
                    continue

                if not phone:
                    self.stderr.write(
                        self.style.WARNING(f"  ⚠  Line {lineno}: empty phone — skipped")
                    )
                    continue

                # Ensure phone starts with +
                if not phone.startswith("+"):
                    phone = f"+{phone}"

                rows.append(
                    {
                        "full_name": full_name,
                        "phone": phone,
                        "notes": notes,
                    }
                )

        return rows

    # ── Preview (dry-run) ─────────────────────────────────────
    def _preview(self, rows: list[dict]):
        self.stdout.write(f"\n{'#':<4} {'Name':<30} {'Phone':<18} {'Notes'}")
        self.stdout.write("─" * 80)
        for i, r in enumerate(rows, start=1):
            self.stdout.write(
                f"{i:<4} {r['full_name']:<30} {r['phone']:<18} {r['notes']}"
            )

    # ── Clear existing data ───────────────────────────────────
    def _clear_existing(self):
        contrib_count = Contribution.objects.count()
        if contrib_count:
            Contribution.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f"  🗑  Deleted {contrib_count} contribution(s).")
            )

        member_count = Member.objects.count()
        if member_count:
            Member.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f"  🗑  Deleted {member_count} member(s).")
            )

    # ── Bulk import ───────────────────────────────────────────
    def _import_members(self, rows: list[dict]) -> tuple[int, int]:
        created = 0
        skipped = 0

        for r in rows:
            _member, was_created = Member.objects.get_or_create(
                phone=r["phone"],
                defaults={
                    "full_name": r["full_name"],
                    "email": "",
                    "is_active": True,
                },
            )

            if was_created:
                created += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✅  Created: {r['full_name']} ({r['phone']})"
                    )
                )
            else:
                skipped += 1
                self.stdout.write(f"  ⏩  Exists:  {r['full_name']} ({r['phone']})")

        return created, skipped
