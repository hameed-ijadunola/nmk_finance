from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


# ──────────────────────────────────────────────
# Member
# ──────────────────────────────────────────────
class Member(models.Model):
    """A community member who may contribute funds."""

    full_name = models.CharField(max_length=150)
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=20, blank=True, default="")
    is_active = models.BooleanField(default=True, help_text="Uncheck to soft-delete.")
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="member_profile",
        help_text="Link to a Django user account for login access.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name


# ──────────────────────────────────────────────
# Categories
# ──────────────────────────────────────────────
class ContributionCategory(models.Model):
    """Type of incoming funds (e.g. Zakat, Sadaqah)."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    show_on_dashboard = models.BooleanField(
        default=True,
        help_text="Show contributions of this category on the public dashboard.",
    )
    include_in_total = models.BooleanField(
        default=True,
        help_text="Include contributions of this category in total income calculations.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Contribution categories"

    def __str__(self):
        return self.name


class ExpenseCategory(models.Model):
    """Type of outgoing funds (e.g. Maintenance, Utilities)."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    show_on_dashboard = models.BooleanField(
        default=True,
        help_text="Show expenses of this category on the public dashboard.",
    )
    include_in_total = models.BooleanField(
        default=True,
        help_text="Include expenses of this category in total expense calculations.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Expense categories"

    def __str__(self):
        return self.name


# ──────────────────────────────────────────────
# Transactions
# ──────────────────────────────────────────────
class Contribution(models.Model):
    """An incoming fund entry tied to a specific member and category."""

    member = models.ForeignKey(
        Member,
        on_delete=models.PROTECT,
        related_name="contributions",
    )
    category = models.ForeignKey(
        ContributionCategory,
        on_delete=models.PROTECT,
        related_name="contributions",
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    date = models.DateTimeField(help_text="When the contribution was made.")
    notes = models.TextField(blank=True, default="")
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_contributions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.member} — {self.category} — ${self.amount:,.2f}"


class Expense(models.Model):
    """An outgoing fund entry tied to a specific category."""

    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name="expenses",
    )
    contribution_category = models.ForeignKey(
        ContributionCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses",
        verbose_name="Fund source",
        help_text="The contribution fund this expense is drawn from (optional).",
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    purpose = models.TextField(
        help_text="What was purchased or the reason for the expense."
    )
    date = models.DateTimeField(help_text="When the expense occurred.")
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_expenses",
    )
    receipt = models.FileField(upload_to="receipts/%Y/%m/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.category} — ${self.amount:,.2f} — {self.purpose[:50]}"


# ──────────────────────────────────────────────
# Site / Dashboard Settings (singleton)
# ──────────────────────────────────────────────
class DashboardSettings(models.Model):
    """Singleton model that controls what general users see on the dashboard."""

    show_summary_cards = models.BooleanField(
        default=True,
        help_text="Show the Total Income / Total Expenses / Net Balance cards to general users.",
    )
    show_recent_contributions = models.BooleanField(
        default=True,
        help_text="Show the Recent Contributions table to general users.",
    )
    show_recent_expenses = models.BooleanField(
        default=True,
        help_text="Show the Recent Expenses table to general users.",
    )

    class Meta:
        verbose_name = "Dashboard Settings"
        verbose_name_plural = "Dashboard Settings"

    def save(self, *args, **kwargs):
        # Enforce singleton: always use pk=1
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # Prevent deletion

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Dashboard Settings"
