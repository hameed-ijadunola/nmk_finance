import django.db.models.deletion
from django.db import migrations, models


def migrate_receipts_forward(apps, schema_editor):
    """Copy any existing single receipt onto the new ExpenseReceipt table."""
    Expense = apps.get_model("finance", "Expense")
    ExpenseReceipt = apps.get_model("finance", "ExpenseReceipt")
    for expense in Expense.objects.exclude(receipt=""):
        if expense.receipt:
            ExpenseReceipt.objects.create(expense=expense, file=expense.receipt)


def migrate_receipts_backward(apps, schema_editor):
    """Put the first receipt back onto the legacy expense.receipt field."""
    ExpenseReceipt = apps.get_model("finance", "ExpenseReceipt")
    for receipt in ExpenseReceipt.objects.order_by("uploaded_at"):
        expense = receipt.expense
        if not expense.receipt:
            expense.receipt = receipt.file
            expense.save(update_fields=["receipt"])


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0005_dashboardsettings"),
    ]

    operations = [
        # 1. Create the new receipts table
        migrations.CreateModel(
            name="ExpenseReceipt",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "expense",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="receipts",
                        to="finance.expense",
                    ),
                ),
                (
                    "file",
                    models.FileField(
                        upload_to="receipts/%Y/%m/",
                        verbose_name="Receipt file",
                    ),
                ),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Receipt",
                "verbose_name_plural": "Receipts",
                "ordering": ["uploaded_at"],
            },
        ),
        # 2. Migrate existing single receipts into the new table
        migrations.RunPython(
            migrate_receipts_forward,
            migrate_receipts_backward,
        ),
        # 3. Drop the old single-file field from Expense
        migrations.RemoveField(
            model_name="expense",
            name="receipt",
        ),
    ]
