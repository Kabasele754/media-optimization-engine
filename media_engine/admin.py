from django.contrib import admin
from .models import MediaAsset, MediaVariant, MediaBinding, PanoramaTile


class MediaVariantInline(admin.TabularInline):
    model = MediaVariant
    extra = 0
    readonly_fields = ('profile', 'width', 'height', 'format', 'file_size', 'quality', 'status', 'processor_version')


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ('id', 'original_name', 'status', 'width', 'height', 'original_size', 'processor_version', 'created_at')
    list_filter = ('status', 'processor_version', 'created_at')
    search_fields = ('original_name', 'original_sha256', 'owner_ref')
    readonly_fields = ('original_sha256', 'width', 'height', 'original_size', 'dominant_color', 'blurhash', 'placeholder_data_url')
    inlines = [MediaVariantInline]


@admin.register(MediaVariant)
class MediaVariantAdmin(admin.ModelAdmin):
    list_display = ('asset', 'profile', 'width', 'height', 'format', 'status', 'file_size', 'processor_version')
    list_filter = ('profile', 'format', 'status', 'processor_version')


@admin.register(MediaBinding)
class MediaBindingAdmin(admin.ModelAdmin):
    list_display = ('content_type', 'object_id', 'field_name', 'profile', 'role', 'asset')
    list_filter = ('profile', 'role', 'content_type')


@admin.register(PanoramaTile)
class PanoramaTileAdmin(admin.ModelAdmin):
    list_display = ('asset', 'profile', 'level', 'col', 'row', 'format', 'status', 'file_size')
    list_filter = ('profile', 'format', 'status', 'level')
    search_fields = ('asset__original_sha256', 'asset__original_name')
