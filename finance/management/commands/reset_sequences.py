"""Reset PostgreSQL sequences to match current table max PK.

This is useful after loading fixtures that insert explicit primary keys (e.g. `loaddata`).

Usage:
    python manage.py reset_sequences finance
    python manage.py reset_sequences admin auth contenttypes finance sessions

Notes:
- Only applies to PostgreSQL; other DB backends will no-op with a warning.
"""

from __future__ import annotations

from typing import Iterable

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.db import DEFAULT_DB_ALIAS, connections


class Command(BaseCommand):
    help = "Reset PostgreSQL sequences for the given app labels."

    def add_arguments(self, parser):
        parser.add_argument(
            "app_labels",
            nargs="*",
            help=(
                "App labels to reset sequences for (e.g. finance auth). "
                "If omitted, resets sequences for all installed apps."
            ),
        )
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help="Nominates a database to reset sequences for. Defaults to 'default'.",
        )

    def handle(self, *args, **options):
        database = options["database"]
        connection = connections[database]

        if connection.vendor != "postgresql":
            self.stdout.write(
                self.style.WARNING(
                    f"Database backend '{connection.vendor}' does not use sequences like PostgreSQL; skipping."
                )
            )
            return

        app_labels: list[str] = options["app_labels"]
        if app_labels:
            app_configs = []
            for label in app_labels:
                try:
                    app_configs.append(apps.get_app_config(label))
                except LookupError as exc:
                    raise CommandError(str(exc)) from exc
        else:
            app_configs = list(apps.get_app_configs())

        models = self._models_for_app_configs(app_configs)
        if not models:
            self.stdout.write(self.style.WARNING("No models found; nothing to reset."))
            return

        statements = connection.ops.sequence_reset_sql(no_style(), models)
        if not statements:
            self.stdout.write(self.style.WARNING("No sequences to reset."))
            return

        with connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)

        self.stdout.write(self.style.SUCCESS("✅ PostgreSQL sequences reset."))

    @staticmethod
    def _models_for_app_configs(app_configs: Iterable) -> list:
        models = []
        for app_config in app_configs:
            models.extend(list(app_config.get_models(include_auto_created=True)))
        return models
