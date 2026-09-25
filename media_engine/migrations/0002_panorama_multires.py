from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('media_engine', '0001_initial')]

    operations = [
        migrations.AddField(model_name='mediaasset', name='media_kind', field=models.CharField(db_index=True, default='image', max_length=32)),
        migrations.AddField(model_name='mediaasset', name='projection', field=models.CharField(blank=True, default='', max_length=32)),
        migrations.AddField(model_name='mediaasset', name='processor', field=models.CharField(blank=True, default='standard_image', max_length=64)),
        migrations.AddField(model_name='mediaasset', name='metadata_json', field=models.JSONField(blank=True, default=dict)),
        migrations.AddField(model_name='mediaasset', name='panorama_preview', field=models.FileField(blank=True, upload_to='media_engine/panoramas/previews/')),
        migrations.CreateModel(
            name='PanoramaTile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('profile', models.CharField(default='panorama.multires', max_length=64)),
                ('processor_version', models.PositiveIntegerField(default=1)),
                ('level', models.PositiveSmallIntegerField()),
                ('level_width', models.PositiveIntegerField(default=0)),
                ('level_height', models.PositiveIntegerField(default=0)),
                ('col', models.PositiveIntegerField()),
                ('row', models.PositiveIntegerField()),
                ('width', models.PositiveIntegerField()),
                ('height', models.PositiveIntegerField()),
                ('format', models.CharField(max_length=10)),
                ('file', models.FileField(upload_to='media_engine/panoramas/')),
                ('file_size', models.BigIntegerField(default=0)),
                ('quality', models.PositiveSmallIntegerField(default=0)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('PROCESSING', 'Processing'), ('READY', 'Ready'), ('FAILED', 'Failed')], default='PENDING', max_length=20)),
                ('last_error', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('asset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='panorama_tiles', to='media_engine.mediaasset')),
            ],
        ),
        migrations.AddConstraint(
            model_name='panoramatile',
            constraint=models.UniqueConstraint(fields=('asset', 'profile', 'processor_version', 'level', 'col', 'row', 'format'), name='uniq_panorama_tile_version'),
        ),
        migrations.AddIndex(model_name='panoramatile', index=models.Index(fields=['asset', 'profile', 'level'], name='media_engin_asset_i_360lvl_idx')),
        migrations.AddIndex(model_name='panoramatile', index=models.Index(fields=['asset', 'status'], name='media_engin_asset_s_360_idx')),
    ]
