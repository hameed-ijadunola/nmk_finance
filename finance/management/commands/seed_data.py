"""
Management command to populate the database with realistic sample data.

Usage:
    python manage.py seed_data
    python manage.py seed_data --clear   # Wipe existing data first
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from finance.models import (
    Contribution,
    ContributionCategory,
    Expense,
    ExpenseCategory,
    Member,
)


class Command(BaseCommand):
    help = "Seed the database with sample members, categories, contributions, and expenses."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing finance data before seeding.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            self.stdout.write("Clearing existing data...")
            Contribution.objects.all().delete()
            Expense.objects.all().delete()
            Member.objects.all().delete()
            ContributionCategory.objects.all().delete()
            ExpenseCategory.objects.all().delete()
            self.stdout.write(self.style.WARNING("All finance data cleared."))

        # ── Contribution Categories ──
        contrib_categories = []
        for name, desc in [
            ("Zakat", "Obligatory annual charity (2.5% of savings)."),
            ("Sadaqah", "Voluntary charitable giving."),
            ("General Fund", "General-purpose community donations."),
        ]:
            cat, created = ContributionCategory.objects.get_or_create(
                name=name, defaults={"description": desc}
            )
            contrib_categories.append(cat)
            status = "Created" if created else "Exists"
            self.stdout.write(f"  [ContributionCategory] {status}: {name}")

        # ── Expense Categories ──
        expense_categories = []
        for name, desc in [
            ("Masjid Maintenance", "Building repairs, cleaning supplies, and upkeep."),
            ("Event Food", "Food and refreshments for community events and Iftar."),
            (
                "Charitable Payouts",
                "Disbursements to those in need within the community.",
            ),
            ("Utilities", "Electricity, water, internet, and phone bills."),
        ]:
            cat, created = ExpenseCategory.objects.get_or_create(
                name=name, defaults={"description": desc}
            )
            expense_categories.append(cat)
            status = "Created" if created else "Exists"
            self.stdout.write(f"  [ExpenseCategory] {status}: {name}")

        # ── Members (loaded from import_members CSV) ──
        # python manage.py import_members              # Add members (skip duplicates)
        # python manage.py import_members --clear      # Replace all members
        # python manage.py import_members --dry-run    # Preview only
        # If no members exist yet, run the CSV import automatically.
        from django.core.management import call_command

        if Member.objects.count() == 0:
            self.stdout.write("  No members found — importing from CSV...")
            call_command("import_members")

        members = list(Member.objects.filter(is_active=True))
        if not members:
            self.stderr.write(
                self.style.ERROR(
                    "  No active members in the database. "
                    "Run 'python manage.py import_members' first."
                )
            )
            return
        self.stdout.write(f"  [Members] {len(members)} active member(s) available.")

        # ── Create a test user linked to the first member ──
        first_member = members[0]
        test_user, user_created = User.objects.get_or_create(
            username="testmember",
            defaults={
                "first_name": first_member.full_name.split()[0],
                "last_name": " ".join(first_member.full_name.split()[1:]),
                "email": first_member.email or "",
            },
        )
        if user_created:
            test_user.set_password("testpass123")
            test_user.save()
            self.stdout.write(
                self.style.SUCCESS("  [User] Created: testmember / testpass123")
            )
        # Link member to user
        first_member = members[0]
        if first_member.user is None:
            first_member.user = test_user
            first_member.save()
            self.stdout.write(f"  [Link] {first_member.full_name} → testmember")

        # ── Get or create admin user for recorded_by ──
        admin_user = User.objects.filter(is_superuser=True).first()

        # ── Sample Contributions ──
        now = timezone.now()
        if Contribution.objects.count() == 0:
            for i in range(15):
                Contribution.objects.create(
                    member=random.choice(members),
                    category=random.choice(contrib_categories),
                    amount=Decimal(random.randint(500, 50000)) + Decimal("0.00"),
                    date=now - timedelta(days=random.randint(1, 180)),
                    notes=random.choice(
                        [
                            "",
                            "Monthly contribution",
                            "Ramadan special",
                            "End of year",
                            "Weekly Jumu'ah contribution",
                        ]
                    ),
                    recorded_by=admin_user,
                )
            self.stdout.write(
                self.style.SUCCESS("  [Contributions] 15 sample records created.")
            )
        else:
            self.stdout.write("  [Contributions] Data already exists, skipping.")

        # ── Sample Expenses ──
        expense_purposes = [
            "Bought 3 new prayer rugs for the main hall",
            "Plumbing repair for wudu area",
            "Monthly electricity bill",
            "Iftar dinner supplies (rice, chicken, drinks)",
            "Emergency aid to Brother Ahmad's family",
            "New PA system microphone",
            "Water dispenser refill (10 bottles)",
            "Community Eid celebration — venue decorations",
        ]
        if Expense.objects.count() == 0:
            for i in range(8):
                Expense.objects.create(
                    category=random.choice(expense_categories),
                    amount=Decimal(random.randint(1000, 30000)) + Decimal("0.00"),
                    purpose=expense_purposes[i],
                    date=now - timedelta(days=random.randint(1, 180)),
                    recorded_by=admin_user,
                )
            self.stdout.write(
                self.style.SUCCESS("  [Expenses] 8 sample records created.")
            )
        else:
            self.stdout.write("  [Expenses] Data already exists, skipping.")

        self.stdout.write(self.style.SUCCESS("\n✅ Seed data complete!"))
        self.stdout.write(
            "  Test member login: username=testmember, password=testpass123"
        )
