from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0002_expense_fund_source"),
    ]

    operations = [
        # Contribution toggles
        migrations.AddField(
            model_name="contribution",
            name="show_on_dashboard",
            field=models.BooleanField(
                default=True,
                help_text="Show this contribution on the public dashboard.",
            ),
        ),
        migrations.AddField(
            model_name="contribution",
            name="include_in_total",
            field=models.BooleanField(
                default=True,
                help_text="Include this contribution in total income calculations.",
            ),
        ),
        # Expense toggles
        migrations.AddField(
            model_name="expense",
            name="show_on_dashboard",
            field=models.BooleanField(
                default=True,
                help_text="Show this expense on the public dashboard.",
            ),
        ),
        migrations.AddField(
            model_name="expense",
            name="include_in_total",
            field=models.BooleanField(
                default=True,
                help_text="Include this expense in total expense calculations.",
            ),
        ),
    ]
