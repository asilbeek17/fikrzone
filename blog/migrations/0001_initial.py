from django.db import migrations, models
import django.db.models.deletion
import django_ckeditor_5.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=60, unique=True)),
                ('slug', models.SlugField(blank=True, unique=True)),
            ],
            options={'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=300)),
                ('slug', models.SlugField(blank=True, max_length=300, unique=True)),
                ('excerpt', models.TextField(blank=True)),
                ('cover_image', models.ImageField(blank=True, null=True, upload_to='covers/')),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('published', 'Published')], default='draft', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('seo_title', models.CharField(blank=True, max_length=200)),
                ('seo_description', models.CharField(blank=True, max_length=300)),
                ('tags', models.ManyToManyField(blank=True, related_name='posts', to='blog.tag')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='ContentBlock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('block_type', models.CharField(choices=[('text', 'Text'), ('image', 'Image'), ('video', 'Video'), ('audio', 'Audio')], default='text', max_length=10)),
                ('position', models.PositiveIntegerField(default=0)),
                ('text_content', django_ckeditor_5.fields.CKEditor5Field(blank=True, verbose_name='Text')),
                ('image', models.ImageField(blank=True, null=True, upload_to='blocks/images/')),
                ('video', models.FileField(blank=True, null=True, upload_to='blocks/videos/')),
                ('audio', models.FileField(blank=True, null=True, upload_to='blocks/audio/')),
                ('caption', models.CharField(blank=True, max_length=300)),
                ('image_layout', models.CharField(blank=True, choices=[('full', 'Full width'), ('wide', 'Wide (80%)'), ('center', 'Centered (60%)'), ('left', 'Float left'), ('right', 'Float right')], default='full', max_length=10)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blocks', to='blog.post')),
            ],
            options={'ordering': ['position']},
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('body', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('approved', models.BooleanField(default=True)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='blog.post')),
            ],
            options={'ordering': ['created_at']},
        ),
        migrations.CreateModel(
            name='Reaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('emoji', models.CharField(choices=[('❤️', 'Heart'), ('🔥', 'Fire'), ('👏', 'Clap'), ('💭', 'Thought'), ('🌿', 'Nature'), ('😮', 'Wow')], max_length=10)),
                ('session_key', models.CharField(max_length=100)),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reactions', to='blog.post')),
            ],
            options={'unique_together': {('post', 'session_key')}},
        ),
    ]
