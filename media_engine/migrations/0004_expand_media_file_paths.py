from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('media_engine', '0003_panorama_cube_tiles')]

    operations = [
        migrations.AlterField(
            model_name='mediaasset',
            name='original_file',
            field=models.FileField(
                max_length=500,
                upload_to='media_engine/originals/',
            ),
        ),
        migrations.AlterField(
            model_name='mediaasset',
            name='panorama_preview',
            field=models.FileField(
                blank=True,
                max_length=500,
                upload_to='media_engine/panoramas/previews/',
            ),
        ),
        migrations.AlterField(
            model_name='mediavariant',
            name='file',
            field=models.FileField(
                max_length=500,
                upload_to='media_engine/derivatives/',
            ),
        ),
        migrations.AlterField(
            model_name='panoramatile',
            name='file',
            field=models.FileField(
                max_length=500,
                upload_to='media_engine/panoramas/',
            ),
        ),
    ]
