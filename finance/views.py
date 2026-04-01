from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.shortcuts import render

from .models import (
    Contribution,
    ContributionCategory,
    DashboardSettings,
    Expense,
    ExpenseCategory,
)

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
ZERO = Decimal("0.00")


def _parse_date_filters(request):
    """Extract optional ?from=YYYY-MM-DD&to=YYYY-MM-DD query params."""
    date_from = request.GET.get("from")
    date_to = request.GET.get("to")
    filters = {}
    if date_from:
        filters["date__date__gte"] = date_from
    if date_to:
        filters["date__date__lte"] = date_to
    return filters, date_from, date_to


def _get_summary():
    """Return total income, total expenses, and net balance (include_in_total only)."""
    total_income = Contribution.objects.filter(
        category__include_in_total=True
    ).aggregate(total=Coalesce(Sum("amount"), ZERO))["total"]
    total_expenses = Expense.objects.filter(category__include_in_total=True).aggregate(
        total=Coalesce(Sum("amount"), ZERO)
    )["total"]
    net_balance = total_income - total_expenses
    return total_income, total_expenses, net_balance


# ──────────────────────────────────────────────
# Public views
# ──────────────────────────────────────────────
def dashboard(request):
    """Main dashboard showing summary cards and recent activity."""
    total_income, total_expenses, net_balance = _get_summary()

    recent_contributions = Contribution.objects.filter(
        category__show_on_dashboard=True
    ).select_related("member", "category")[:5]
    recent_expenses = Expense.objects.filter(
        category__show_on_dashboard=True
    ).select_related("category")[:5]

    income_by_category = (
        Contribution.objects.filter(category__show_on_dashboard=True)
        .values("category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )
    expense_by_category = (
        Expense.objects.filter(category__show_on_dashboard=True)
        .values("category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )

    context = {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "net_balance": net_balance,
        "recent_contributions": recent_contributions,
        "recent_expenses": recent_expenses,
        "income_by_category": income_by_category,
        "expense_by_category": expense_by_category,
        "dash_settings": DashboardSettings.get_solo(),
    }

    if getattr(request, "htmx", False):
        return render(request, "partials/summary_cards.html", context)

    return render(request, "dashboard.html", context)


def contributions_view(request):
    """Contribution breakdown page with date filtering."""
    date_filters, date_from, date_to = _parse_date_filters(request)
    is_staff = request.user.is_staff

    # Non-staff only see contributions from dashboard-visible categories
    base_filter = {**date_filters}
    if not is_staff:
        base_filter["category__show_on_dashboard"] = True

    contributions = (
        Contribution.objects.filter(**base_filter)
        .select_related("member", "category")
        .order_by("-date")
    )

    by_category = (
        Contribution.objects.filter(**base_filter)
        .values(
            "category__name",
            "category__show_on_dashboard",
            "category__include_in_total",
        )
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )

    grand_total = contributions.filter(category__include_in_total=True).aggregate(
        total=Coalesce(Sum("amount"), ZERO)
    )["total"]

    categories = ContributionCategory.objects.filter(is_active=True)

    context = {
        "contributions": contributions,
        "by_category": by_category,
        "grand_total": grand_total,
        "categories": categories,
        "date_from": date_from or "",
        "date_to": date_to or "",
        "dash_settings": DashboardSettings.get_solo(),
    }

    if getattr(request, "htmx", False):
        return render(request, "partials/contributions_table.html", context)

    return render(request, "contributions.html", context)


def expenses_view(request):
    """Expense breakdown page with date filtering."""
    date_filters, date_from, date_to = _parse_date_filters(request)
    is_staff = request.user.is_staff

    # Non-staff only see expenses from dashboard-visible categories
    base_filter = {**date_filters}
    if not is_staff:
        base_filter["category__show_on_dashboard"] = True

    expenses = (
        Expense.objects.filter(**base_filter)
        .select_related("category", "contribution_category")
        .order_by("-date")
    )

    by_category = (
        Expense.objects.filter(**base_filter)
        .values(
            "category__name",
            "category__show_on_dashboard",
            "category__include_in_total",
        )
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )

    by_fund_source = (
        Expense.objects.filter(**base_filter)
        .exclude(contribution_category__isnull=True)
        .values("contribution_category__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    )

    grand_total = expenses.filter(category__include_in_total=True).aggregate(
        total=Coalesce(Sum("amount"), ZERO)
    )["total"]

    categories = ExpenseCategory.objects.filter(is_active=True)

    context = {
        "expenses": expenses,
        "by_category": by_category,
        "by_fund_source": by_fund_source,
        "grand_total": grand_total,
        "categories": categories,
        "date_from": date_from or "",
        "date_to": date_to or "",
        "dash_settings": DashboardSettings.get_solo(),
    }

    if getattr(request, "htmx", False):
        return render(request, "partials/expenses_table.html", context)

    return render(request, "expenses.html", context)


# ──────────────────────────────────────────────
# Authenticated member views
# ──────────────────────────────────────────────
@login_required
def my_contributions(request):
    """Show the logged-in member's personal contribution history."""
    member = getattr(request.user, "member_profile", None)

    if member is None:
        return render(
            request,
            "my_contributions.html",
            {
                "contributions": [],
                "grand_total": ZERO,
                "no_profile": True,
            },
        )

    date_filters, date_from, date_to = _parse_date_filters(request)

    contributions = (
        member.contributions.filter(**date_filters)
        .select_related("category")
        .order_by("-date")
    )

    grand_total = contributions.aggregate(total=Coalesce(Sum("amount"), ZERO))["total"]

    context = {
        "member": member,
        "contributions": contributions,
        "grand_total": grand_total,
        "date_from": date_from or "",
        "date_to": date_to or "",
    }

    if getattr(request, "htmx", False):
        return render(request, "partials/my_contributions_table.html", context)

    return render(request, "my_contributions.html", context)


# ──────────────────────────────────────────────
# HTMX partial endpoints
# ──────────────────────────────────────────────
def htmx_summary_cards(request):
    total_income, total_expenses, net_balance = _get_summary()
    return render(
        request,
        "partials/summary_cards.html",
        {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_balance": net_balance,
        },
    )
