import uuid
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class MediaAsset(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        READY = 'READY', 'Ready'
        PARTIAL = 'PARTIAL', 'Partial'
        FAILED = 'FAILED', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_sha256 = models.CharField(max_length=64, unique=True, db_index=True)
    original_file = models.FileField(upload_to='media_engine/originals/', max_length=500)
    original_name = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=100)
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    original_size = models.BigIntegerField(default=0)
    media_kind = models.CharField(max_length=32, default='image', db_index=True)
    projection = models.CharField(max_length=32, blank=True, default='')
    processor = models.CharField(max_length=64, blank=True, default='standard_image')
    metadata_json = models.JSONField(default=dict, blank=True)
    panorama_preview = models.FileField(upload_to='media_engine/panoramas/previews/', blank=True, max_length=500)
    dominant_color = models.CharField(max_length=16, blank=True)
    blurhash = models.CharField(max_length=255, blank=True)
    placeholder_data_url = models.TextField(blank=True)
    focal_x = models.FloatField(null=True, blank=True)
    focal_y = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    last_error = models.TextField(blank=True)
    processor_version = models.PositiveIntegerField(default=1)
    processed_at = models.DateTimeField(null=True, blank=True)
    owner_ref = models.CharField(max_length=255, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.id} {self.original_name or self.original_sha256[:12]}'


class MediaVariant(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        READY = 'READY', 'Ready'
        FAILED = 'FAILED', 'Failed'

    asset = models.ForeignKey(MediaAsset, related_name='variants', on_delete=models.CASCADE)
    profile = models.CharField(max_length=50, default='default')
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField(default=0)
    format = models.CharField(max_length=10)
    file = models.FileField(upload_to='media_engine/derivatives/', max_length=500)
    file_size = models.BigIntegerField(default=0)
    quality = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    processor_version = models.PositiveIntegerField(default=1)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['asset', 'profile', 'width', 'format', 'processor_version'],
                name='uniq_media_variant_version',
            )
        ]
        indexes = [
            models.Index(fields=['asset', 'profile', 'status'], name='media_engin_asset_i_60f63d_idx'),
            models.Index(fields=['processor_version', 'status'], name='media_engin_process_7c2c36_idx'),
        ]

    def __str__(self):
        return f'{self.asset_id} {self.profile} {self.width}.{self.format}'


class PanoramaTile(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        READY = 'READY', 'Ready'
        FAILED = 'FAILED', 'Failed'

    asset = models.ForeignKey(MediaAsset, related_name='panorama_tiles', on_delete=models.CASCADE)
    build = models.ForeignKey('PanoramaBuild', null=True, blank=True, related_name='tiles', on_delete=models.CASCADE)
    profile = models.CharField(max_length=64, default='panorama.multires')
    processor_version = models.PositiveIntegerField(default=1)
    level = models.PositiveSmallIntegerField()
    face = models.CharField(max_length=1, blank=True, default='')
    level_width = models.PositiveIntegerField(default=0)
    level_height = models.PositiveIntegerField(default=0)
    col = models.PositiveIntegerField()
    row = models.PositiveIntegerField()
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    format = models.CharField(max_length=10)
    file = models.FileField(upload_to='media_engine/panoramas/', max_length=500)
    file_size = models.BigIntegerField(default=0)
    quality = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['asset', 'profile', 'processor_version', 'level', 'face', 'col', 'row', 'format'],
                condition=models.Q(build__isnull=True),
                name='uniq_panorama_tile_legacy',
            ),
            models.UniqueConstraint(
                fields=['build', 'level', 'face', 'col', 'row', 'format'],
                name='uniq_panorama_build_tile',
            )
        ]
        indexes = [
            models.Index(fields=['asset', 'profile', 'level'], name='media_engin_asset_i_360lvl_idx'),
            models.Index(fields=['asset', 'status'], name='media_engin_asset_s_360_idx'),
            models.Index(
                fields=['asset', 'profile', 'level', 'face'],
                name='media_engin_cube_face_idx',
            ),
        ]

    def __str__(self):
        return f"{self.asset_id} L{self.level} {self.face or 'eq'} {self.col},{self.row}.{self.format}"


class MediaBinding(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=128)
    content_object = GenericForeignKey('content_type', 'object_id')
    field_name = models.CharField(max_length=100)
    profile = models.CharField(max_length=50, default='default')
    role = models.CharField(max_length=50, default='content')
    asset = models.ForeignKey(MediaAsset, related_name='bindings', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['content_type', 'object_id', 'field_name'],
                name='uniq_media_binding_field',
            )
        ]


class PanoramaBuild(models.Model):
    """An immutable output namespace; only complete levels are published."""

    class State(models.TextChoices):
        PROCESSING = 'PROCESSING', 'Processing'
        PREVIEW_READY = 'PREVIEW_READY', 'Preview ready'
        BASE_LEVEL_READY = 'BASE_LEVEL_READY', 'Base level ready'
        READY = 'READY', 'Ready'
        FAILED = 'FAILED', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(MediaAsset, related_name='panorama_builds', on_delete=models.CASCADE)
    profile = models.CharField(max_length=64)
    processor_version = models.PositiveIntegerField()
    fingerprint = models.CharField(max_length=64)
    config = models.JSONField(default=dict)
    state = models.CharField(max_length=24, choices=State.choices, default=State.PROCESSING)
    preview = models.FileField(upload_to='media_engine/panoramas/', max_length=500, blank=True)
    # Store storage keys, never expiring signed URLs, in this snapshot.
    manifest = models.JSONField(default=dict)
    is_active = models.BooleanField(default=False)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['asset', 'profile'], condition=models.Q(is_active=True),
                                    name='uniq_active_panorama_build'),
        ]
        indexes = [models.Index(fields=['asset', 'profile', 'fingerprint'], name='moe_pano_build_lookup')]


class MediaProcessingLease(models.Model):
    """Portable, database-backed lease with owner-checked renewal/release."""
    key = models.CharField(max_length=255, primary_key=True)
    owner = models.CharField(max_length=32)
    expires_at = models.DateTimeField(db_index=True)
