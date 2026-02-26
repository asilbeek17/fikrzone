from django.db import models
from django.utils.text import slugify
from django.urls import reverse
from django_ckeditor_5.fields import CKEditor5Field


class Tag(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('blog:tag', kwargs={'slug': self.slug})


class Post(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_PUBLISHED, 'Published'),
    ]

    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300, unique=True, blank=True)
    excerpt = models.TextField(blank=True, help_text="Short summary shown on listing pages")
    cover_image = models.ImageField(upload_to='covers/', blank=True, null=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    view_count = models.PositiveIntegerField(default=0)

    seo_title = models.CharField(max_length=200, blank=True)
    seo_description = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            n = 1
            while Post.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('blog:post_detail', kwargs={'slug': self.slug})

    @property
    def meta_title(self):
        return self.seo_title or self.title

    @property
    def meta_description(self):
        return self.seo_description or self.excerpt

    @property
    def reaction_summary(self):
        summary = {}
        for r in self.reactions.all():
            summary[r.emoji] = summary.get(r.emoji, 0) + 1
        return summary

    @property
    def word_count(self):
        total = 0
        for block in self.blocks.all():
            if block.block_type == 'text' and block.text_content:
                import re
                text = re.sub(r'<[^>]+>', '', block.text_content)
                total += len(text.split())
        return total

    @property
    def mood(self):
        hour = self.created_at.hour
        if 0 <= hour < 6:
            return "🌙 Kecha yozilgan"
        elif 6 <= hour < 12:
            return "🌅 Ertalab yozilgan"
        elif 12 <= hour < 18:
            return "☀️ Tushdan keyin yozilgan"
        else:
            return "🌆 Kechqurun yozilgan"


class ContentBlock(models.Model):
    TYPE_TEXT  = 'text'
    TYPE_IMAGE = 'image'
    TYPE_VIDEO = 'video'
    TYPE_AUDIO = 'audio'

    BLOCK_TYPES = [
        (TYPE_TEXT,  'Text'),
        (TYPE_IMAGE, 'Image'),
        (TYPE_VIDEO, 'Video'),
        (TYPE_AUDIO, 'Audio'),
    ]

    post         = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='blocks')
    block_type   = models.CharField(max_length=10, choices=BLOCK_TYPES, default=TYPE_TEXT)
    position     = models.PositiveIntegerField(default=0)

    # Text block
    text_content = CKEditor5Field('Text', config_name='default', blank=True)

    # Media blocks
    image        = models.ImageField(upload_to='blocks/images/', blank=True, null=True)
    video        = models.FileField(upload_to='blocks/videos/', blank=True, null=True)
    audio        = models.FileField(upload_to='blocks/audio/',  blank=True, null=True)
    caption      = models.CharField(max_length=300, blank=True, help_text='Optional caption shown below the media')

    # Image display options
    IMAGE_FULL   = 'full'
    IMAGE_WIDE   = 'wide'
    IMAGE_CENTER = 'center'
    IMAGE_LEFT   = 'left'
    IMAGE_RIGHT  = 'right'
    IMAGE_LAYOUT_CHOICES = [
        (IMAGE_FULL,   'Full width'),
        (IMAGE_WIDE,   'Wide (80%)'),
        (IMAGE_CENTER, 'Centered (60%)'),
        (IMAGE_LEFT,   'Float left'),
        (IMAGE_RIGHT,  'Float right'),
    ]
    image_layout = models.CharField(max_length=10, choices=IMAGE_LAYOUT_CHOICES, default=IMAGE_FULL, blank=True)

    class Meta:
        ordering = ['position']

    def __str__(self):
        return f"{self.get_block_type_display()} block #{self.position} — {self.post.title}"


EMOJI_CHOICES = [
    ('❤️', 'Heart'),
    ('🔥', 'Fire'),
    ('👏', 'Clap'),
    ('💭', 'Thought'),
    ('🌿', 'Nature'),
    ('😮', 'Wow'),
]


class Reaction(models.Model):
    post        = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reactions')
    emoji       = models.CharField(max_length=10, choices=EMOJI_CHOICES)
    session_key = models.CharField(max_length=100)

    class Meta:
        unique_together = ('post', 'session_key')

    def __str__(self):
        return f"{self.emoji} on {self.post.title}"


class Comment(models.Model):
    post       = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    name       = models.CharField(max_length=100)
    body       = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    approved   = models.BooleanField(default=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.name} on {self.post.title}"
