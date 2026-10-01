import hashlib
import io
import json
from datetime import timedelta
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np
from PIL import Image
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from media_engine.models import MediaAsset, PanoramaBuild, PanoramaTile, MediaProcessingLease
from media_engine.locks import cache_lock, ProcessingLease, LeaseLost
from media_engine.manifest import build_manifest
from media_engine.adapters.marzipano import to_marzipano
from media_engine.processors.panorama.equirectangular import Panorama360Processor, PanoramaBusy
from media_engine.processors.panorama.publication import snapshot, publish
from media_engine.processors.panorama.cube_tiles import cube_level_sizes, generate_cube_level
from media_engine.processors.panorama.cubemap import iter_cubemap_faces
from media_engine.queueing import queue_for_profile, enqueue_asset
from media_engine.views import MediaViewSet


@override_settings(MEDIA_ENGINE_PIPELINE_VERSION=7, MEDIA_ENGINE_PANORAMA_CUBE_MIN_SIZE=64,
    MEDIA_ENGINE_PANORAMA_CUBE_MAX_SIZE=128, MEDIA_ENGINE_PANORAMA_TILE_SIZE=64,
    MEDIA_ENGINE_PANORAMA_CUBE_FORMAT='webp', MEDIA_ENGINE_PANORAMA_GENERATE_CUBEMAP=False)
class PanoramaPublicationTests(TestCase):
    def setUp(self):
        self.root = TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.override = override_settings(MEDIA_ROOT=self.root.name)
        self.override.enable()
        self.addCleanup(self.override.disable)
        cache.clear()
        data = np.zeros((256, 512, 3), dtype=np.uint8)
        data[..., 0] = np.arange(512, dtype=np.uint16)[None, :] % 256
        data[..., 1] = np.arange(256, dtype=np.uint8)[:, None]
        image = Image.fromarray(data)
        output = io.BytesIO()
        image.save(output, 'PNG')
        raw = output.getvalue()
        self.asset = MediaAsset.objects.create(original_sha256=hashlib.sha256(raw).hexdigest(),
            original_file=ContentFile(raw, name='source.png'), original_name='source.png',
            mime_type='image/png', width=512, height=256, original_size=len(raw), media_kind='panorama',
            projection='equirectangular', processor_version=7)
        self.processor = Panorama360Processor()
        self.profile = 'panorama.marzipano'

    def generate(self):
        self.processor.process(self.asset, self.profile)
        self.asset.refresh_from_db()
        return PanoramaBuild.objects.get(asset=self.asset, profile=self.profile, is_active=True)

    def test_preview_is_committed_before_any_tiles(self):
        build = self.processor.prepare(self.asset, self.profile)
        self.asset.refresh_from_db()
        self.assertEqual(build.state, 'PREVIEW_READY')
        self.assertEqual(self.asset.panorama_preview.name, build.preview.name)
        self.assertTrue(default_storage.exists(build.preview.name))
        self.assertFalse(build.tiles.exists())
        manifest = build_manifest(self.asset, self.profile)
        self.assertTrue(manifest['preview'])
        self.assertFalse(manifest['ready'])

    def test_complete_pyramid_and_frozen_dimensions(self):
        build = self.generate()
        manifest = build_manifest(self.asset, self.profile)
        self.assertTrue(manifest['complete'])
        self.assertEqual(manifest['revision'], str(build.pk))
        self.assertEqual(len(manifest['levels']), 2)
        self.assertEqual(build.tiles.count(), 30)
        with override_settings(MEDIA_ENGINE_PANORAMA_TILE_SIZE=512):
            self.assertEqual(build_manifest(self.asset, self.profile)['levels'][0]['tile_size'], 64)

    def test_incomplete_manifest_does_not_stick_for_an_hour(self):
        build = self.processor.prepare(self.asset, self.profile)
        before = build_manifest(self.asset, self.profile)
        self.assertFalse(before['levels'])
        self.processor.render(build.pk)
        after = build_manifest(self.asset, self.profile)
        self.assertTrue(after['complete'])
        self.assertTrue(after['levels'])

    def test_force_creates_new_urls_and_preserves_previous_files(self):
        old = self.generate()
        old_names = set(old.tiles.values_list('file', flat=True))
        old_preview = old.preview.name
        new = self.processor.prepare(self.asset, self.profile, force=True)
        self.assertNotEqual(old.pk, new.pk)
        self.assertEqual(build_manifest(self.asset, self.profile)['revision'], str(old.pk))
        self.processor.render(new.pk)
        self.assertEqual(build_manifest(self.asset, self.profile)['revision'], str(new.pk))
        self.assertTrue(old_names.isdisjoint(new.tiles.values_list('file', flat=True)))
        self.assertTrue(all(default_storage.exists(name) for name in old_names | {old_preview}))
        self.assertEqual(PanoramaBuild.objects.filter(asset=self.asset, is_active=True).count(), 1)

    def test_completed_build_skips_source_decode_and_projection(self):
        self.generate()
        with patch('media_engine.processors.panorama.equirectangular.normalized_image', side_effect=AssertionError('unexpected decode')):
            self.processor.process(self.asset, self.profile)

    def test_failed_rebuild_keeps_last_complete_generation_active(self):
        old = self.generate()
        new = self.processor.prepare(self.asset, self.profile, force=True)
        with patch('media_engine.processors.panorama.equirectangular.generate_cube_level', side_effect=RuntimeError('worker interrupted')):
            with self.assertRaises(RuntimeError):
                self.processor.render(new.pk)
        manifest = build_manifest(self.asset, self.profile)
        self.assertEqual(manifest['revision'], str(old.pk))
        self.assertTrue(manifest['complete'])

    def test_completed_base_is_published_and_retry_skips_it(self):
        build = self.processor.prepare(self.asset, self.profile)
        seen = []
        def interrupt(asset, image, **kwargs):
            if kwargs['plan'].level == 1:
                visible = build_manifest(self.asset, self.profile)
                self.assertTrue(visible['ready'])
                self.assertFalse(visible['complete'])
                self.assertEqual(len(visible['levels']), 1)
                raise RuntimeError('interrupted after base')
            return generate_cube_level(asset, image, **kwargs)
        with patch('media_engine.processors.panorama.equirectangular.generate_cube_level', side_effect=interrupt):
            with self.assertRaises(RuntimeError):
                self.processor.render(build.pk)
        def record(asset, image, **kwargs):
            seen.append(kwargs['plan'].level)
            return generate_cube_level(asset, image, **kwargs)
        with patch('media_engine.processors.panorama.equirectangular.generate_cube_level', side_effect=record):
            self.processor.render(build.pk)
        self.assertEqual(seen, [1])
        self.assertTrue(build_manifest(self.asset, self.profile)['complete'])

    def test_missing_coordinate_cannot_be_published_as_complete(self):
        build = self.generate()
        build.tiles.filter(level=1, face='f', row=0, col=0).delete()
        self.assertEqual(len(snapshot(build)['levels']), 1)
        with cache_lock('validation-test', wait_timeout=0) as lease:
            with self.assertRaises(ValueError):
                publish(build, lease, final=True)

    def test_wrong_tile_dimensions_reject_level(self):
        build = self.generate()
        build.tiles.filter(level=0, face='u').update(width=63)
        self.assertEqual(snapshot(build)['levels'], [])

    def test_compact_url_template_matches_explicit_urls(self):
        self.generate()
        explicit = to_marzipano(build_manifest(self.asset, self.profile))
        compact = to_marzipano(build_manifest(self.asset, self.profile, compact=True))
        self.assertNotIn('tiles', compact)
        self.assertIn('urlTemplate', compact)
        for tile in explicit['tiles']:
            url = compact['urlTemplate']
            for key, value in {'z': tile['z'], 'f': tile['face'], 'x': tile['x'], 'y': tile['y']}.items():
                url = url.replace('{' + key + '}', str(value))
            self.assertEqual(url, tile['url'])
        self.assertLess(len(json.dumps(compact)), len(json.dumps(explicit)))

    def test_signed_urls_are_resolved_fresh_and_never_templated(self):
        self.generate()
        stamp = [1]
        def signed(name):
            return f'https://objects.example/{name}?signature={stamp[0]}'
        with patch.object(default_storage, 'url', side_effect=signed):
            first = to_marzipano(build_manifest(self.asset, self.profile, compact=True))
            stamp[0] = 2
            second = to_marzipano(build_manifest(self.asset, self.profile, compact=True))
        self.assertNotIn('urlTemplate', first)
        self.assertIn('signature=1', first['tiles'][0]['url'])
        self.assertIn('signature=2', second['tiles'][0]['url'])

    def test_cdn_prefix_is_applied_to_preview_and_compact_tiles(self):
        self.generate()
        with override_settings(MEDIA_ENGINE_CDN_BASE_URL='https://cdn.example'):
            result = to_marzipano(build_manifest(self.asset, self.profile, compact=True))
        self.assertTrue(result['preview'].startswith('https://cdn.example/'))
        self.assertTrue(result['urlTemplate'].startswith('https://cdn.example/'))

    def test_settings_change_creates_distinct_generation(self):
        previous = self.generate()
        with override_settings(MEDIA_ENGINE_PANORAMA_CUBE_QUALITY=45):
            new = self.processor.prepare(self.asset, self.profile)
        self.assertNotEqual(previous.fingerprint, new.fingerprint)
        self.assertNotEqual(previous.pk, new.pk)

    def test_legacy_rows_are_filtered_by_version(self):
        self.asset.status = 'READY'
        self.asset.metadata_json = {'panorama_pipeline': {'levels': 1}}
        self.asset.save()
        for version in (7, 8):
            for face in ('f', 'b', 'l', 'r', 'u', 'd'):
                PanoramaTile.objects.create(asset=self.asset, profile=self.profile, processor_version=version,
                    level=0, face=face, col=0, row=0, width=64, height=64, level_width=64, level_height=64,
                    format='webp', file=f'legacy/v{version}/{face}.webp', file_size=10, status='READY')
        manifest = build_manifest(self.asset, self.profile)
        self.assertTrue(manifest['complete'])
        urls = [tile['url'] for tile in manifest['levels'][0]['formats']['webp']]
        self.assertEqual(len(urls), 6)
        self.assertTrue(all('/v7/' in url for url in urls))

    def test_empty_or_holey_levels_are_not_ready(self):
        PanoramaTile.objects.create(asset=self.asset, profile=self.profile, processor_version=7,
            level=0, face='f', col=0, row=0, width=64, height=64, level_width=64, level_height=64,
            format='webp', file='incomplete.webp', file_size=10, status='READY')
        self.assertFalse(build_manifest(self.asset, self.profile)['ready'])

    def test_only_base_level_remains_selectable(self):
        build = self.processor.prepare(self.asset, self.profile)
        def only_base(asset, image, **kwargs):
            if kwargs['plan'].level:
                raise RuntimeError('pause')
            return generate_cube_level(asset, image, **kwargs)
        with patch('media_engine.processors.panorama.equirectangular.generate_cube_level', side_effect=only_base):
            with self.assertRaises(RuntimeError):
                self.processor.render(build.pk)
        adapted = to_marzipano(build_manifest(self.asset, self.profile))
        self.assertFalse(adapted['geometry']['levels'][0]['fallbackOnly'])

    def test_parallel_prepare_is_rejected_by_lease(self):
        with cache_lock(f'moe:panorama:{self.asset.pk}:{self.profile}', wait_timeout=0):
            with self.assertRaises(PanoramaBusy):
                self.processor.prepare(self.asset, self.profile)

    def test_manifest_etag_is_private_and_conditional(self):
        self.generate()
        factory = APIRequestFactory()
        view = MediaViewSet.as_view({'get': 'panorama'})
        url = '/?adapter=marzipano&profile=panorama.marzipano&representation=compact'
        response = view(factory.get(url), pk=self.asset.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'private, no-cache')
        self.assertIn('Cookie', response['Vary'])
        again = view(factory.get(url, HTTP_IF_NONE_MATCH=response['ETag']), pk=self.asset.pk)
        self.assertEqual(again.status_code, 304)

    def test_audit_detects_missing_storage_file(self):
        build = self.generate()
        default_storage.delete(build.tiles.first().file.name)
        output = io.StringIO()
        with self.assertRaises(CommandError):
            call_command('audit_panorama_media', profile=self.profile, check_files=True,
                         fail_on_incomplete=True, stdout=output)
        self.assertIn('complete=False', output.getvalue())

    def test_equirectangular_profile_and_optional_cube_still_work(self):
        with override_settings(MEDIA_ENGINE_PANORAMA_FORMATS=('webp',), MEDIA_ENGINE_PANORAMA_MIN_LEVEL_WIDTH=256,
                MEDIA_ENGINE_PANORAMA_GENERATE_CUBEMAP=True, MEDIA_ENGINE_PANORAMA_CUBEMAP_FACE_SIZE=32):
            self.processor.process(self.asset, 'panorama.multires')
        manifest = build_manifest(self.asset, 'panorama.multires')
        self.assertEqual(manifest['layout'], 'equirectangular-grid')
        self.assertTrue(manifest['complete'])
        self.assertEqual(len(manifest['cubemap']['faces']), 6)

    def test_backfill_can_target_existing_panorama_profile(self):
        with patch('media_engine.management.commands.backfill_panorama_media.enqueue_asset') as enqueue:
            call_command('backfill_panorama_media', profile=self.profile, limit=1, stdout=io.StringIO())
        self.assertEqual(enqueue.call_args.kwargs['profile'], self.profile)
        self.assertTrue(enqueue.call_args.kwargs['backfill'])


    def test_benchmark_reports_smaller_compact_descriptor(self):
        self.generate()
        output = io.StringIO()
        call_command('benchmark_panorama_manifest', asset_id=str(self.asset.pk), runs=2, stdout=output)
        report = json.loads(output.getvalue())
        self.assertLess(report['results']['compact']['json_bytes'], report['results']['explicit']['json_bytes'])

    def test_interrupted_face_resumes_without_rewriting_completed_face(self):
        build = self.processor.prepare(self.asset, self.profile)
        from media_engine.processors.panorama.cubemap import iter_cubemap_faces as original
        def interrupted(*args, **kwargs):
            for index, item in enumerate(original(*args, **kwargs)):
                if index == 2:
                    raise RuntimeError('interrupted conversion')
                yield item
        with patch('media_engine.processors.panorama.cube_tiles.iter_cubemap_faces', side_effect=interrupted):
            with self.assertRaises(RuntimeError):
                self.processor.render(build.pk)
        written = dict(build.tiles.values_list('id', 'file'))
        self.assertEqual(len(written), 2)
        self.processor.render(build.pk)
        self.assertEqual(written, dict(build.tiles.filter(pk__in=written).values_list('id', 'file')))
        self.assertTrue(build_manifest(self.asset, self.profile)['complete'])

    def test_storage_collision_forces_explicit_urls_not_broken_template(self):
        build = self.generate()
        tile = build.tiles.first()
        tile.file.name += '.alternative'
        tile.save()
        with cache_lock('collision-publication', wait_timeout=0) as lease:
            publish(build, lease, final=True)
        manifest = build_manifest(self.asset, self.profile, compact=True)
        self.assertNotIn('url_template', manifest)


class ProcessingLeaseTests(TestCase):
    def test_expired_owner_cannot_release_new_owner(self):
        old = ProcessingLease('shared')
        self.assertTrue(old.acquire())
        MediaProcessingLease.objects.filter(key='shared').update(expires_at=timezone.now()-timedelta(seconds=1))
        new = ProcessingLease('shared')
        self.assertTrue(new.acquire())
        old.release()
        self.assertEqual(MediaProcessingLease.objects.get(key='shared').owner, new.owner)
        new.release()

    def test_lost_lease_cannot_publish_or_renew(self):
        old = ProcessingLease('shared')
        old.acquire()
        MediaProcessingLease.objects.filter(key='shared').update(owner='replacement')
        with self.assertRaises(LeaseLost):
            old.checkpoint(force=True)
        with self.assertRaises(LeaseLost):
            with old.guard():
                self.fail('must not publish')
        old.release()

    def test_context_releases_after_exception(self):
        with self.assertRaises(ValueError):
            with cache_lock('test', wait_timeout=0):
                raise ValueError('test')
        self.assertFalse(MediaProcessingLease.objects.filter(key='test').exists())


class PanoramaConfigurationTests(SimpleTestCase):
    def test_bad_cube_sizes_are_rejected(self):
        for low, high in [(300, 4096), (512, 256), (256, 3000)]:
            with self.assertRaises(ValueError):
                cube_level_sizes(8192, min_size=low, max_size=high)

    def test_banded_projection_is_deterministic(self):
        image = Image.fromarray(np.random.default_rng(42).integers(0, 256, (32, 64, 3), dtype=np.uint8))
        first = dict(iter_cubemap_faces(image, 16, rows_per_chunk=1))
        second = dict(iter_cubemap_faces(image, 16, rows_per_chunk=16))
        for name in first:
            np.testing.assert_array_equal(np.asarray(first[name]), np.asarray(second[name]))

    def test_tiles_do_not_share_priority_queue_with_heroes(self):
        self.assertEqual(queue_for_profile('hero'), 'image_critical')
        self.assertEqual(queue_for_profile('panorama.marzipano'), 'image_normal')
        self.assertEqual(queue_for_profile('panorama.marzipano', backfill=True), 'image_backfill')

    @override_settings(MEDIA_ENGINE_TASK_MODE='celery', MEDIA_ENGINE_PANORAMA_STAGED_TASKS=True)
    def test_staged_queue_prepares_preview_first(self):
        with patch('media_engine.tasks.prepare_panorama_asset.apply_async') as enqueue:
            enqueue_asset('asset-id', profile='panorama.marzipano')
        self.assertEqual(enqueue.call_args.kwargs['queue'], 'image_critical')
        self.assertEqual(enqueue.call_args.kwargs['args'][0], 'asset-id')
