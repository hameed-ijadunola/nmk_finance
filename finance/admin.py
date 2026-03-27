import csv

from django.contrib import admin
from django.db.models import Sum
from django.http import HttpResponse
from django.utils.html import format_html

from .forms import ContributionAdminForm, ExpenseAdminForm
from .models import (
    Contribution,
    ContributionCategory,
    DashboardSettings,
    Expense,
    ExpenseCategory,
    Member,
)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def export_as_csv(modeladmin, request, queryset):
    """Generic admin action to export selected rows as CSV."""
    meta = modeladmin.model._meta
    field_names = [f.name for f in meta.fields]

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f"attachment; filename={meta.verbose_name_plural}.csv"
    )

    writer = csv.writer(response)
    writer.writerow(field_names)
    for obj in queryset:
        writer.writerow([getattr(obj, f) for f in field_names])

    return response


export_as_csv.short_description = "Export selected as CSV"


# ──────────────────────────────────────────────
# Admin site config
# ──────────────────────────────────────────────
admin.site.site_header = "NMK Community Finance"
admin.site.site_title = "NMK Finance Admin"
admin.site.index_title = "Finance Dashboard"


# ──────────────────────────────────────────────
# Member
# ──────────────────────────────────────────────
class ContributionInline(admin.TabularInline):
    """Show a member's contributions directly on their detail page."""

    model = Contribution
    extra = 0
    fields = ("date", "category", "amount", "notes")
    readonly_fields = ("date", "category", "amount", "notes")
    ordering = ("-date",)
    show_change_link = True
    verbose_name = "Contribution"
    verbose_name_plural = "Contribution History"

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "email",
        "phone",
        "is_active",
        "contribution_count",
        "total_contributed",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = ("full_name", "email", "phone")
    list_per_page = 25
    actions = [export_as_csv]
    inlines = [ContributionInline]
    fieldsets = (
        (
            "Personal Details",
            {
                "fields": ("full_name", "email", "phone"),
            },
        ),
        (
            "Account",
            {
                "fields": ("user", "is_active"),
            },
        ),
    )

    @admin.display(description="Contributions")
    def contribution_count(self, obj):
        count = obj.contributions.count()
        url = f"/admin/finance/contribution/?member__id__exact={obj.pk}"
        return format_html(
            '<a href="{}">{} record{}</a>', url, count, "s" if count != 1 else ""
        )

    @admin.display(description="Total Contributed")
    def total_contributed(self, obj):
        total = obj.contributions.aggregate(t=Sum("amount"))["t"] or 0
        return format_html("<strong>${}</strong>", f"{total:,.2f}")


# ──────────────────────────────────────────────
# Categories
# ──────────────────────────────────────────────
@admin.register(ContributionCategory)
class ContributionCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "is_active",
        "show_on_dashboard",
        "include_in_total",
        "created_at",
    )
    list_editable = ("show_on_dashboard", "include_in_total")
    list_filter = ("is_active", "show_on_dashboard", "include_in_total")
    search_fields = ("name",)  # required for autocomplete_fields on ExpenseAdmin


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "is_active",
        "show_on_dashboard",
        "include_in_total",
        "created_at",
    )
    list_editable = ("show_on_dashboard", "include_in_total")
    list_filter = ("is_active", "show_on_dashboard", "include_in_total")
    search_fields = ("name",)


# ──────────────────────────────────────────────
# Contribution
# ──────────────────────────────────────────────
@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    form = ContributionAdminForm
    list_display = (
        "member",
        "category",
        "formatted_amount",
        "date",
        "recorded_by",
    )
    list_filter = ("category", "date")
    search_fields = ("member__full_name", "notes")
    autocomplete_fields = ("member",)
    date_hierarchy = "date"
    list_per_page = 30
    actions = [export_as_csv]

    @admin.display(description="Amount")
    def formatted_amount(self, obj):
        return format_html("<strong>${}</strong>", f"{obj.amount:,.2f}")

    def save_model(self, request, obj, form, change):
        if not change:
            obj.recorded_by = request.user
        super().save_model(request, obj, form, change)

    def changelist_view(self, request, extra_context=None):
        # Inject total into the changelist page
        response = super().changelist_view(request, extra_context)
        if hasattr(response, "context_data") and "cl" in response.context_data:
            qs = response.context_data["cl"].queryset
            total = qs.aggregate(total=Sum("amount"))["total"] or 0
            response.context_data["total"] = total
        return response


# ──────────────────────────────────────────────
# Expense
# ──────────────────────────────────────────────
@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    form = ExpenseAdminForm
    list_display = (
        "category",
        "fund_source",
        "formatted_amount",
        "short_purpose",
        "date",
        "recorded_by",
    )
    list_filter = ("category", "contribution_category", "date")
    search_fields = ("purpose",)
    date_hierarchy = "date"
    list_per_page = 30
    actions = [export_as_csv]
    autocomplete_fields = ("contribution_category",)

    @admin.display(description="Fund Source")
    def fund_source(self, obj):
        if obj.contribution_category:
            return format_html(
                '<span style="color:#0369a1">{}</span>',
                obj.contribution_category.name,
            )
        return format_html('<span style="color:#94a3b8">—</span>')

    @admin.display(description="Amount")
    def formatted_amount(self, obj):
        return format_html("<strong>${}</strong>", f"{obj.amount:,.2f}")

    @admin.display(description="Purpose")
    def short_purpose(self, obj):
        return obj.purpose[:80] + "…" if len(obj.purpose) > 80 else obj.purpose

    def save_model(self, request, obj, form, change):
        if not change:
            obj.recorded_by = request.user
        super().save_model(request, obj, form, change)

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context)
        if hasattr(response, "context_data") and "cl" in response.context_data:
            qs = response.context_data["cl"].queryset
            total = qs.aggregate(total=Sum("amount"))["total"] or 0
            response.context_data["total"] = total
        return response


# ──────────────────────────────────────────────
# Dashboard Settings (singleton)
# ──────────────────────────────────────────────
@admin.register(DashboardSettings)
class DashboardSettingsAdmin(admin.ModelAdmin):
    """Singleton admin: the list view redirects straight to the one record."""

    def has_add_permission(self, request):
        return not DashboardSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        from django.shortcuts import redirect

        obj = DashboardSettings.get_solo()
        return redirect(f"/admin/finance/dashboardsettings/{obj.pk}/change/")
