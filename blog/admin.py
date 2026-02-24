from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import Post, Tag, Comment, Reaction, ContentBlock


# ─── Content Block Inline ────────────────────────────────────────────────────
class ContentBlockInline(admin.StackedInline):
    model = ContentBlock
    extra = 0
    fields = (
        'block_type', 'position',
        'text_content',
        'image', 'image_layout',
        'video',
        'audio',
        'caption',
    )
    ordering = ['position']

    class Media:
        css = {'all': ('blog/css/block_editor.css',)}
        js  = (
            'https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js',
            'blog/js/block_editor.js',
        )


# ─── Tag admin ───────────────────────────────────────────────────────────────
@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display  = ('name', 'slug', 'post_count')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

    def post_count(self, obj):
        c = obj.posts.count()
        return format_html('<span style="background:#4f46e5;color:#fff;padding:2px 10px;border-radius:99px;font-size:.75rem;font-weight:700;">{}</span>', c)
    post_count.short_description = 'Posts'


# ─── Post admin ──────────────────────────────────────────────────────────────
@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display  = ('post_id', 'title_col', 'tag_list', 'block_count', 'created_at', 'cover_thumb', 'view_link')
    list_filter   = ('status', 'tags', 'created_at')
    search_fields = ('title', 'excerpt')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('tags',)
    readonly_fields   = ('created_at', 'updated_at', 'cover_preview')
    date_hierarchy    = 'created_at'
    list_per_page     = 20
    inlines           = [ContentBlockInline]

    fieldsets = (
        ('Post Info', {
            'fields': ('title', 'slug', 'excerpt', 'status', 'tags'),
        }),
        ('Cover Image', {
            'fields': ('cover_image', 'cover_preview'),
            'classes': ('collapse',),
        }),
        ('SEO (optional)', {
            'fields': ('seo_title', 'seo_description'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def post_id(self, obj):
        return format_html('<code style="color:#818cf8;font-size:.8rem;">#{}</code>', obj.id)
    post_id.short_description = '#'
    post_id.admin_order_field = 'id'

    def title_col(self, obj):
        color = '#22c55e' if obj.status == 'published' else '#f59e0b'
        label = obj.status.upper()
        return format_html(
            '{} <span style="background:{};color:#fff;padding:2px 9px;border-radius:99px;font-size:.68rem;font-weight:700;">{}</span>',
            obj.title, color, label
        )
    title_col.short_description = 'Title'

    def tag_list(self, obj):
        tags = obj.tags.all()
        if not tags:
            return format_html('<span style="color:#555">—</span>')
        pills = ''.join(
            f'<span style="background:#1e1e28;color:#818cf8;border:1px solid #3a3a48;padding:2px 8px;border-radius:99px;font-size:.68rem;margin-right:3px;">#{t.name}</span>'
            for t in tags
        )
        return format_html(mark_safe(pills))
    tag_list.short_description = 'Tags'

    def block_count(self, obj):
        n = obj.blocks.count()
        return format_html('<span style="color:#818cf8;font-weight:700;">{} block{}</span>', n, 's' if n != 1 else '')
    block_count.short_description = 'Blocks'

    def cover_thumb(self, obj):
        if obj.cover_image:
            return format_html('<img src="{}" style="height:38px;width:56px;object-fit:cover;border-radius:5px;border:1px solid #333;" />', obj.cover_image.url)
        return format_html('<span style="color:#555;font-size:.75rem;">—</span>')
    cover_thumb.short_description = 'Cover'

    def cover_preview(self, obj):
        if obj.cover_image:
            return format_html('<img src="{}" style="max-width:440px;border-radius:10px;border:1px solid #333;" />', obj.cover_image.url)
        return '—'
    cover_preview.short_description = 'Preview'

    def view_link(self, obj):
        if obj.status == 'published':
            return format_html('<a href="{}" target="_blank" style="color:#818cf8;font-size:.8rem;">View →</a>', obj.get_absolute_url())
        return format_html('<span style="color:#555;font-size:.8rem;">Draft</span>')
    view_link.short_description = ''


# ─── Comment admin ────────────────────────────────────────────────────────────
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display  = ('name', 'post', 'created_at', 'approved')
    list_filter   = ('approved', 'created_at')
    search_fields = ('name', 'body', 'post__title')
    list_editable = ('approved',)
    readonly_fields = ('created_at',)
    actions = ['approve', 'unapprove']

    def approve(self, request, qs):
        qs.update(approved=True)
    approve.short_description = 'Approve selected'

    def unapprove(self, request, qs):
        qs.update(approved=False)
    unapprove.short_description = 'Unapprove selected'


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ('emoji', 'post', 'session_key')
    list_filter  = ('emoji',)
