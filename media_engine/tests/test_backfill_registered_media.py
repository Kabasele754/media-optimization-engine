from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase


class _Manager:
    def __init__(self, objects):
        self._objects = list(objects)

    def all(self):
        return self

    def __iter__(self):
        return iter(self._objects)

    def __getitem__(self, item):
        if isinstance(item, slice):
            return _Manager(self._objects[item])
        return self._objects[item]

    def iterator(self):
        return iter(self._objects)


class BackfillRegisteredMediaTests(TestCase):
    @patch("media_engine.management.commands.backfill_registered_media.entries")
    @patch("media_engine.management.commands.backfill_registered_media.ingest_model_field")
    def test_invalid_image_does_not_abort_backfill(self, ingest, entries):
        model = SimpleNamespace(
            _default_manager=_Manager([
                SimpleNamespace(pk=1),
                SimpleNamespace(pk=2),
            ]),
            _meta=SimpleNamespace(label="demo.Photo", db_table="demo_photo"),
        )
        entries.return_value = [
            SimpleNamespace(
                model=model,
                field_name="image",
                profile="default",
                role="content",
            )
        ]
        ingest.side_effect = [ValidationError("Unsupported image format"), object()]

        call_command("backfill_registered_media")

        self.assertEqual(ingest.call_count, 2)
