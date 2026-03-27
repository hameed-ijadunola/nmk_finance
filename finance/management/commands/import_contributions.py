"""
Management command to bulk create or update contributions from a CSV file.

Match key: member_name + category  (one contribution per member per category).
- If no match exists  → create a new Contribution.
- If a match exists   → update amount/date only when the values differ.
- If member or category is not found in the DB → warn and skip the row.

Usage:
    python manage.py import_contributions
    python manage.py import_contributions --csv data/my_file.csv
    python manage.py import_contributions --dry-run
    python manage.py import_contributions --create-categories
"""

import csv
from datetime import datetime, time
from datetime import timezone as dt_timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from finance.models import Contribution, ContributionCategory, Member

DEFAULT_CSV = (
    Path(__file__).resolve().parents[3] / "data" / "3_27_contribution_import.csv"
)


class Command(BaseCommand):
    help = "Bulk create or update contributions from a flat CSV file."

    # ── CLI flags ──────────────────────────────────────────────────────────────
    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            dest="csv_path",
            default=str(DEFAULT_CSV),
            help="Path to the CSV file (default: data/3_27_contribution_import.csv).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without writing to the database.",
        )
        parser.add_argument(
            "--create-categories",
            action="store_true",
            help="Auto-create missing ContributionCategory entries instead of skipping them.",
        )

    # ── Main handler ───────────────────────────────────────────────────────────
    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        dry_run = options["dry_run"]
        create_cats = options["create_categories"]

        if not csv_path.exists():
            raise CommandError(f"CSV file not found: {csv_path}")

        rows = self._read_csv(csv_path)
        self.stdout.write(f"\n📄  {len(rows)} data rows found in {csv_path.name}\n")

        if dry_run:
            self._preview(rows)
            self.stdout.write(
                self.style.WARNING("\n🚫  Dry-run — no changes written.\n")
            )
            return

        with transaction.atomic():
            stats = self._process(rows, create_cats)

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅  Done — "
                f"{stats['created']} created, "
                f"{stats['updated']} updated, "
                f"{stats['skipped']} unchanged, "
                f"{stats['errors']} skipped (errors).\n"
            )
        )

    # ── CSV reader ─────────────────────────────────────────────────────────────
    def _read_csv(self, path: Path) -> list[dict]:
        required = {"member_name", "category", "amount", "date"}
        rows: list[dict] = []

        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            if not required.issubset(set(reader.fieldnames or [])):
                raise CommandError(
                    f"CSV is missing required columns. "
                    f"Expected {required}, got {reader.fieldnames}"
                )

            for lineno, row in enumerate(reader, start=2):
                member_name = (row.get("member_name") or "").strip()
                category = (row.get("category") or "").strip()
                amount_raw = (row.get("amount") or "").strip()
                date_raw = (row.get("date") or "").strip()

                # ── Basic validation ──
                if not member_name or not category or not amount_raw or not date_raw:
                    self.stderr.write(
                        self.style.WARNING(
                            f"  ⚠  Line {lineno}: incomplete row — skipped"
                        )
                    )
                    continue

                try:
                    amount = Decimal(amount_raw)
                except InvalidOperation:
                    self.stderr.write(
                        self.style.WARNING(
                            f"  ⚠  Line {lineno}: invalid amount '{amount_raw}' — skipped"
                        )
                    )
                    continue

                try:
                    date = datetime.strptime(date_raw, "%Y-%m-%d").date()
                except ValueError:
                    self.stderr.write(
                        self.style.WARNING(
                            f"  ⚠  Line {lineno}: invalid date '{date_raw}' — skipped"
                        )
                    )
                    continue

                rows.append(
                    {
                        "member_name": member_name,
                        "category": category,
                        "amount": amount,
                        "date": date,
                        "lineno": lineno,
                    }
                )

        return rows

    # ── Preview (dry-run) ──────────────────────────────────────────────────────
    def _preview(self, rows: list[dict]):
        self.stdout.write(
            f"\n{'#':<5} {'Member':<28} {'Category':<42} {'Amount':>8}  {'Date'}"
        )
        self.stdout.write("─" * 100)
        for i, r in enumerate(rows, start=1):
            self.stdout.write(
                f"{i:<5} {r['member_name']:<28} {r['category']:<42} "
                f"${r['amount']:>7,.2f}  {r['date']}"
            )

    # ── Core processing ────────────────────────────────────────────────────────
    def _process(self, rows: list[dict], create_cats: bool) -> dict:
        stats = {"created": 0, "updated": 0, "skipped": 0, "errors": 0}

        # Cache lookups to avoid hitting the DB on every row
        member_cache: dict[str, Member | None] = {}
        cat_cache: dict[str, ContributionCategory | None] = {}

        for r in rows:
            # ── Resolve Member ──
            name = r["member_name"]
            if name not in member_cache:
                try:
                    member_cache[name] = Member.objects.get(full_name=name)
                except Member.DoesNotExist:
                    member_cache[name] = None
                    self.stderr.write(
                        self.style.WARNING(
                            f"  ⚠  Line {r['lineno']}: member '{name}' not found — skipped"
                        )
                    )
                except Member.MultipleObjectsReturned:
                    member_cache[name] = None
                    self.stderr.write(
                        self.style.WARNING(
                            f"  ⚠  Line {r['lineno']}: multiple members match '{name}' — skipped"
                        )
                    )

            member = member_cache[name]
            if member is None:
                stats["errors"] += 1
                continue

            # ── Resolve Category ──
            cat_name = r["category"]
            if cat_name not in cat_cache:
                if create_cats:
                    cat, was_created = ContributionCategory.objects.get_or_create(
                        name=cat_name, defaults={"is_active": True}
                    )
                    if was_created:
                        self.stdout.write(
                            self.style.SUCCESS(f"  ➕  Created category: {cat_name}")
                        )
                    cat_cache[cat_name] = cat
                else:
                    try:
                        cat_cache[cat_name] = ContributionCategory.objects.get(
                            name=cat_name
                        )
                    except ContributionCategory.DoesNotExist:
                        cat_cache[cat_name] = None
                        self.stderr.write(
                            self.style.WARNING(
                                f"  ⚠  Line {r['lineno']}: category '{cat_name}' not found "
                                f"(use --create-categories to auto-create) — skipped"
                            )
                        )
                    except ContributionCategory.MultipleObjectsReturned:
                        cat_cache[cat_name] = None
                        self.stderr.write(
                            self.style.WARNING(
                                f"  ⚠  Line {r['lineno']}: multiple categories match '{cat_name}' — skipped"
                            )
                        )

            category = cat_cache[cat_name]
            if category is None:
                stats["errors"] += 1
                continue

            # ── Convert date → aware datetime (noon UTC) ──
            naive_dt = datetime.combine(r["date"], time(12, 0, 0))
            aware_dt = timezone.make_aware(naive_dt, dt_timezone.utc)

            # ── Update-or-create (key: member + category) ──
            try:
                contribution = Contribution.objects.get(
                    member=member, category=category
                )
                # Check if anything actually changed
                changed_fields = []
                if contribution.amount != r["amount"]:
                    changed_fields.append(
                        f"amount {contribution.amount} → {r['amount']}"
                    )
                    contribution.amount = r["amount"]
                if contribution.date.date() != r["date"]:
                    changed_fields.append(
                        f"date {contribution.date.date()} → {r['date']}"
                    )
                    contribution.date = aware_dt

                if changed_fields:
                    contribution.save(update_fields=["amount", "date"])
                    self.stdout.write(
                        f"  🔄  Updated: {name} / {cat_name} — "
                        + ", ".join(changed_fields)
                    )
                    stats["updated"] += 1
                else:
                    self.stdout.write(f"  ⏩  Unchanged: {name} / {cat_name}")
                    stats["skipped"] += 1

            except Contribution.DoesNotExist:
                Contribution.objects.create(
                    member=member,
                    category=category,
                    amount=r["amount"],
                    date=aware_dt,
                )
                self.stdout.write(
                    self.style.SUCCESS(f"  ✅  Created: {name} / {cat_name}")
                )
                stats["created"] += 1

        return stats
