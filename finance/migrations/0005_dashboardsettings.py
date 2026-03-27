from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0004_category_toggles"),
    ]

    operations = [
        migrations.CreateModel(
            name="DashboardSettings",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "show_summary_cards",
                    models.BooleanField(
                        default=True,
                        help_text="Show the Total Income / Total Expenses / Net Balance cards to general users.",
                    ),
                ),
                (
                    "show_recent_contributions",
                    models.BooleanField(
                        default=True,
                        help_text="Show the Recent Contributions table to general users.",
                    ),
                ),
                (
                    "show_recent_expenses",
                    models.BooleanField(
                        default=True,
                        help_text="Show the Recent Expenses table to general users.",
                    ),
                ),
            ],
            options={
                "verbose_name": "Dashboard Settings",
                "verbose_name_plural": "Dashboard Settings",
            },
        ),
    ]
