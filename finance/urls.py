from django.urls import path

from . import views

app_name = "finance"

urlpatterns = [
    # Public dashboard
    path("", views.dashboard, name="dashboard"),
    path("contributions/", views.contributions_view, name="contributions"),
    path("expenses/", views.expenses_view, name="expenses"),
    # Authenticated member area
    path("my/contributions/", views.my_contributions, name="my_contributions"),
    # HTMX partials
    path("htmx/summary-cards/", views.htmx_summary_cards, name="htmx_summary_cards"),
    path(
        "htmx/contributions-table/",
        views.contributions_view,
        name="htmx_contributions_table",
    ),
    path("htmx/expenses-table/", views.expenses_view, name="htmx_expenses_table"),
    path(
        "htmx/my-contributions/", views.my_contributions, name="htmx_my_contributions"
    ),
]
