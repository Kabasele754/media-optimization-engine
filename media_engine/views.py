from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from .manifest import build_manifest
from .models import MediaAsset, MediaVariant
from .profiles import get_profile
from .serializers import MediaUploadSerializer, MediaAssetSerializer
from .services import ingest_uploaded_file, generate_variant
from .queueing import enqueue_asset
from .auth import MediaEngineApiKeyPermission
from .node import scoped_owner_ref


class MediaViewSet(ViewSet):
    permission_classes = [MediaEngineApiKeyPermission]

    def create(self, request):
        serializer = MediaUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        asset, created = ingest_uploaded_file(
            data['file'],
            owner_ref=scoped_owner_ref(data.get('owner_ref', '')),
            focal_x=data.get('focal_x'),
            focal_y=data.get('focal_y'),
            profile=data.get('profile', 'default'),
            media_kind=data.get('media_kind', ''),
            projection=data.get('projection', ''),
            enqueue=True,
        )
        output = MediaAssetSerializer(asset, context={'profile': data.get('profile', 'default')}).data
        return Response(output, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        asset = get_object_or_404(MediaAsset, pk=pk)
        profile = request.query_params.get('profile', 'default')
        return Response(MediaAssetSerializer(asset, context={'profile': profile}).data)

    def partial_update(self, request, pk=None):
        asset = get_object_or_404(MediaAsset, pk=pk)
        changed = False
        for field in ('focal_x', 'focal_y'):
            if field in request.data:
                value = float(request.data[field])
                if not 0 <= value <= 1:
                    return Response({field: 'Must be between 0 and 1.'}, status=400)
                setattr(asset, field, value)
                changed = True
        if changed:
            asset.save(update_fields=['focal_x', 'focal_y', 'updated_at'])
        return Response(MediaAssetSerializer(asset).data)

    @action(detail=True, methods=['post'])
    def regenerate(self, request, pk=None):
        asset = get_object_or_404(MediaAsset, pk=pk)
        profile = request.data.get('profile', 'default')
        enqueue_asset(asset.id, profile=profile, force=True)
        return Response({'id': str(asset.id), 'status': 'queued', 'profile': profile}, status=202)

    @action(detail=True, methods=['get'])
    def manifest(self, request, pk=None):
        asset = get_object_or_404(MediaAsset, pk=pk)
        profile = request.query_params.get('profile', 'default')
        return Response(build_manifest(asset, profile=profile))

    @action(detail=True, methods=['get'])
    def panorama(self, request, pk=None):
        asset = get_object_or_404(MediaAsset, pk=pk)
        profile = request.query_params.get('profile', 'panorama.multires')
        manifest = build_manifest(asset, profile=profile)
        adapter = request.query_params.get('adapter', 'generic').lower()
        if adapter == 'pannellum':
            from .adapters.pannellum import to_pannellum
            manifest = to_pannellum(manifest)
        elif adapter == 'marzipano':
            from .adapters.marzipano import to_marzipano
            manifest = to_marzipano(manifest)
        elif adapter == 'threejs':
            from .adapters.threejs import to_threejs
            manifest = to_threejs(manifest)
        elif adapter != 'generic':
            return Response({'adapter': 'Unsupported adapter.'}, status=400)
        return Response(manifest)

    @action(detail=True, methods=['get'])
    def render(self, request, pk=None):
        asset = get_object_or_404(MediaAsset, pk=pk)
        profile_name = request.query_params.get('profile', 'default')
        profile = get_profile(profile_name)
        fmt = request.query_params.get('format', 'avif').lower()
        width = int(request.query_params.get('width', 640))
        if fmt not in set(profile.get('formats', [])) | {profile.get('fallback_format', 'jpeg')}:
            return Response({'format': 'Unsupported format.'}, status=400)
        width = min(width, asset.width)
        variant = MediaVariant.objects.filter(
            asset=asset,
            profile=profile_name,
            width=width,
            format=fmt,
            processor_version=getattr(settings, 'MEDIA_ENGINE_PIPELINE_VERSION', 1),
            status=MediaVariant.Status.READY,
        ).first()
        if variant is None:
            variant = generate_variant(asset, profile_name=profile_name, width=width, fmt=fmt)
        if variant is None:
            return Response({'status': 'processing', 'retry_after': 1}, status=202)
        return HttpResponseRedirect(variant.file.url)
