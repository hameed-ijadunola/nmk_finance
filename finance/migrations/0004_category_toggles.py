from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0003_toggle_flags"),
    ]

    operations = [
        # ── Move flags off individual records ──
        migrations.RemoveField(model_name="contribution", name="show_on_dashboard"),
        migrations.RemoveField(model_name="contribution", name="include_in_total"),
        migrations.RemoveField(model_name="expense", name="show_on_dashboard"),
        migrations.RemoveField(model_name="expense", name="include_in_total"),
        # ── Add flags to ContributionCategory ──
        migrations.AddField(
            model_name="contributioncategory",
            name="show_on_dashboard",
            field=models.BooleanField(
                default=True,
                help_text="Show contributions of this category on the public dashboard.",
            ),
        ),
        migrations.AddField(
            model_name="contributioncategory",
            name="include_in_total",
            field=models.BooleanField(
                default=True,
                help_text="Include contributions of this category in total income calculations.",
            ),
        ),
        # ── Add flags to ExpenseCategory ──
        migrations.AddField(
            model_name="expensecategory",
            name="show_on_dashboard",
            field=models.BooleanField(
                default=True,
                help_text="Show expenses of this category on the public dashboard.",
            ),
        ),
        migrations.AddField(
            model_name="expensecategory",
            name="include_in_total",
            field=models.BooleanField(
                default=True,
                help_text="Include expenses of this category in total expense calculations.",
            ),
        ),
    ]
