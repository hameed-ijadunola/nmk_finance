from datetime import time

from django import forms
from django.contrib.admin.widgets import AdminSplitDateTime

from .models import Contribution, Expense


class NoonDefaultSplitDateTimeField(forms.SplitDateTimeField):
    """A SplitDateTimeField whose time portion is optional.

    When the user supplies a date but leaves the time blank, the time
    is automatically set to 12:00:00 (noon).
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", AdminSplitDateTime)
        super().__init__(*args, **kwargs)
        # Allow the time sub-field to be empty
        self.fields[1].required = False

    def compress(self, data_list):
        if data_list:
            # Require at least a date
            if not data_list[0]:
                raise forms.ValidationError(
                    self.error_messages["invalid_date"], code="invalid_date"
                )
            # Default missing time to noon
            if not data_list[1]:
                data_list = [data_list[0], time(12, 0, 0)]
        return super().compress(data_list)


class ContributionAdminForm(forms.ModelForm):
    date = NoonDefaultSplitDateTimeField(
        label="Date",
        help_text="Enter a date (time defaults to 12:00 noon if left blank).",
    )

    class Meta:
        model = Contribution
        fields = "__all__"


class ExpenseAdminForm(forms.ModelForm):
    date = NoonDefaultSplitDateTimeField(
        label="Date",
        help_text="Enter a date (time defaults to 12:00 noon if left blank).",
    )

    class Meta:
        model = Expense
        fields = "__all__"
