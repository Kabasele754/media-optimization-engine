# Generated for Media Optimization Engine 1.0.0
import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [('contenttypes', '0002_remove_content_type_name')]

    operations = [
        migrations.CreateModel(
            name='MediaAsset',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('original_sha256', models.CharField(db_index=True, max_length=64, unique=True)),
                ('original_file', models.FileField(upload_to='media_engine/originals/')),
                ('original_name', models.CharField(blank=True, max_length=255)),
                ('mime_type', models.CharField(max_length=100)),
                ('width', models.PositiveIntegerField()),
                ('height', models.PositiveIntegerField()),
                ('original_size', models.BigIntegerField(default=0)),
                ('dominant_color', models.CharField(blank=True, max_length=16)),
                ('blurhash', models.CharField(blank=True, max_length=255)),
                ('placeholder_data_url', models.TextField(blank=True)),
                ('focal_x', models.FloatField(blank=True, null=True)),
                ('focal_y', models.FloatField(blank=True, null=True)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('PROCESSING', 'Processing'), ('READY', 'Ready'), ('PARTIAL', 'Partial'), ('FAILED', 'Failed')], default='PENDING', max_length=20)),
                ('last_error', models.TextField(blank=True)),
                ('processor_version', models.PositiveIntegerField(default=1)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('owner_ref', models.CharField(blank=True, db_index=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='MediaVariant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('profile', models.CharField(default='default', max_length=50)),
                ('width', models.PositiveIntegerField()),
                ('height', models.PositiveIntegerField(default=0)),
                ('format', models.CharField(max_length=10)),
                ('file', models.FileField(upload_to='media_engine/derivatives/')),
                ('file_size', models.BigIntegerField(default=0)),
                ('quality', models.PositiveSmallIntegerField(default=0)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('PROCESSING', 'Processing'), ('READY', 'Ready'), ('FAILED', 'Failed')], default='PENDING', max_length=20)),
                ('processor_version', models.PositiveIntegerField(default=1)),
                ('last_error', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('asset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='variants', to='media_engine.mediaasset')),
            ],
        ),
        migrations.CreateModel(
            name='MediaBinding',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.CharField(max_length=128)),
                ('field_name', models.CharField(max_length=100)),
                ('profile', models.CharField(default='default', max_length=50)),
                ('role', models.CharField(default='content', max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('asset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bindings', to='media_engine.mediaasset')),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
            ],
        ),
        migrations.AddConstraint(
            model_name='mediavariant',
            constraint=models.UniqueConstraint(fields=('asset', 'profile', 'width', 'format', 'processor_version'), name='uniq_media_variant_version'),
        ),
        migrations.AddIndex(
            model_name='mediavariant',
            index=models.Index(fields=['asset', 'profile', 'status'], name='media_engin_asset_i_60f63d_idx'),
        ),
        migrations.AddIndex(
            model_name='mediavariant',
            index=models.Index(fields=['processor_version', 'status'], name='media_engin_process_7c2c36_idx'),
        ),
        migrations.AddConstraint(
            model_name='mediabinding',
            constraint=models.UniqueConstraint(fields=('content_type', 'object_id', 'field_name'), name='uniq_media_binding_field'),
        ),
    ]
