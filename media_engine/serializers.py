from rest_framework import serializers
from .models import MediaAsset
from .manifest import build_manifest


class MediaUploadSerializer(serializers.Serializer):
    file = serializers.ImageField()
    profile = serializers.CharField(required=False, default='default')
    owner_ref = serializers.CharField(required=False, allow_blank=True, default='')
    focal_x = serializers.FloatField(required=False, min_value=0, max_value=1)
    focal_y = serializers.FloatField(required=False, min_value=0, max_value=1)
    media_kind = serializers.ChoiceField(required=False, choices=['image', 'panorama'])
    projection = serializers.ChoiceField(required=False, choices=['equirectangular', 'cubemap'])


class MediaAssetSerializer(serializers.ModelSerializer):
    manifest = serializers.SerializerMethodField()

    class Meta:
        model = MediaAsset
        fields = [
            'id', 'status', 'original_name', 'mime_type', 'width', 'height',
            'original_size', 'media_kind', 'projection', 'processor', 'dominant_color', 'blurhash', 'focal_x', 'focal_y',
            'processor_version', 'last_error', 'created_at', 'updated_at', 'manifest',
        ]

    def get_manifest(self, obj):
        profile = self.context.get('profile', 'default')
        return build_manifest(obj, profile=profile)
