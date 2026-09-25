from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('media_engine', '0002_panorama_multires')]

    operations = [
        migrations.RemoveConstraint(
            model_name='panoramatile',
            name='uniq_panorama_tile_version',
        ),
        migrations.AddField(
            model_name='panoramatile',
            name='face',
            field=models.CharField(blank=True, default='', max_length=1),
        ),
        migrations.AddConstraint(
            model_name='panoramatile',
            constraint=models.UniqueConstraint(
                fields=('asset', 'profile', 'processor_version', 'level', 'face', 'col', 'row', 'format'),
                name='uniq_panorama_tile_version_v2',
            ),
        ),
        migrations.AddIndex(
            model_name='panoramatile',
            index=models.Index(
                fields=['asset', 'profile', 'level', 'face'],
                name='media_engin_cube_face_idx',
            ),
        ),
    ]
