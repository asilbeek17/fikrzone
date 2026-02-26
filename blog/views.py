import json
import os
import re
import subprocess
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Q, Count
from django.db import models
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils.text import slugify
from .models import Post, Tag, Comment, Reaction, ContentBlock, EMOJI_CHOICES


def is_staff(user):
    return user.is_active and user.is_staff


def _sidebar_posts():
    return Post.objects.prefetch_related('tags').order_by('-id')


# ─── Public views ─────────────────────────────────────────────────────────────

def home(request):
    posts    = Post.objects.filter(status='published').prefetch_related('tags').order_by('-created_at')
    page_obj = Paginator(posts, 3).get_page(request.GET.get('page'))
    # Safely resolve cover URLs so template never crashes on missing files
    for p in page_obj:
        try:
            p.cover_url = p.cover_image.url if p.cover_image else None
        except Exception:
            p.cover_url = None
    all_tags = Tag.objects.annotate(
        pub_count=Count('posts', filter=Q(posts__status='published'))
    ).filter(pub_count__gt=0)
    return render(request, 'blog/home.html', {
        'page_obj': page_obj, 'all_tags': all_tags,
        'sidebar_posts': _sidebar_posts(),
        'seo_title': 'Asilbek Abdurahmonov — Shaxsiy Blog',
        'seo_description': 'Fikrlar va hayot haqida yozilgan maqolalar.',
    })


def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug)
    if post.status != 'published' and not request.user.is_staff:
        from django.http import Http404
        raise Http404

    # Count view once per session per post
    viewed_key = f'viewed_post_{post.pk}'
    if not request.session.get(viewed_key):
        Post.objects.filter(pk=post.pk).update(view_count=models.F('view_count') + 1)
        post.view_count += 1
        request.session[viewed_key] = True

    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    user_reaction = None
    try:
        user_reaction = Reaction.objects.get(post=post, session_key=session_key).emoji
    except Reaction.DoesNotExist:
        pass

    reaction_data = sorted([{
        'emoji': e, 'label': _label,
        'count': post.reaction_summary.get(e, 0),
        'active': user_reaction == e,
    } for e, _label in EMOJI_CHOICES], key=lambda x: x['count'], reverse=True)

    blocks   = post.blocks.all().order_by('position')
    try:
        post.cover_url = post.cover_image.url if post.cover_image else None
    except Exception:
        post.cover_url = None
    comments = post.comments.filter(approved=True)
    related  = Post.objects.filter(
        status='published', tags__in=post.tags.all()
    ).exclude(id=post.id).distinct().order_by('-created_at')[:3]

    return render(request, 'blog/post_detail.html', {
        'post': post, 'blocks': blocks,
        'comments': comments, 'reaction_data': reaction_data,
        'related': related, 'sidebar_posts': _sidebar_posts(),
        'seo_title': post.meta_title,
        'seo_description': post.meta_description,
        'seo_keywords': ', '.join(t.name for t in post.tags.all()),
    })


def tag_posts(request, slug):
    tag      = get_object_or_404(Tag, slug=slug)
    posts    = Post.objects.filter(status='published', tags=tag).prefetch_related('tags').order_by('-created_at')
    page_obj = Paginator(posts, 6).get_page(request.GET.get('page'))
    for p in page_obj:
        try:
            p.cover_url = p.cover_image.url if p.cover_image else None
        except Exception:
            p.cover_url = None
    all_tags = Tag.objects.annotate(
        pub_count=Count('posts', filter=Q(posts__status='published'))
    ).filter(pub_count__gt=0)
    return render(request, 'blog/tag.html', {
        'tag': tag, 'page_obj': page_obj, 'all_tags': all_tags,
        'sidebar_posts': _sidebar_posts(),
        'seo_title': f'#{tag.name} — Editorial',
    })


def search(request):
    q       = request.GET.get('q', '').strip()
    results = []
    if q:
        results = Post.objects.filter(status='published').filter(
            Q(title__icontains=q) | Q(excerpt__icontains=q) |
            Q(tags__name__icontains=q) | Q(blocks__text_content__icontains=q)
        ).distinct().order_by('-created_at')
    return render(request, 'blog/search.html', {
        'q': q, 'results': results,
        'sidebar_posts': _sidebar_posts(),
        'seo_title': f'Qidirish: {q} — Asilbek Abdurahmonov' if q else 'Search — Asilbek Abdurahmonov',
    })


# ─── Auth views ───────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('blog:editor_create')
    error = None
    if request.method == 'POST':
        user = authenticate(request,
            username=request.POST.get('username'),
            password=request.POST.get('password'))
        if user and user.is_staff:
            login(request, user)
            return redirect(request.GET.get('next') or 'blog:editor_create')
        error = 'Invalid credentials or not a staff member.'
    return render(request, 'blog/login.html', {'error': error})


def logout_view(request):
    logout(request)
    return redirect('blog:home')


# ─── Editor (staff only) ──────────────────────────────────────────────────────

@user_passes_test(is_staff, login_url='/login/')
def editor(request, slug=None):
    post     = None
    blocks   = []
    all_tags = Tag.objects.all().order_by('name')

    if slug:
        post   = get_object_or_404(Post, slug=slug)
        blocks = list(post.blocks.all().order_by('position').values(
            'id', 'block_type', 'position', 'text_content',
            'caption', 'image_layout',
            'image', 'video', 'audio',
        ))
        # Convert file paths to URLs
        from django.conf import settings
        for b in blocks:
            for field in ('image', 'video', 'audio'):
                if b[field]:
                    b[field + '_url'] = settings.MEDIA_URL + b[field]
                else:
                    b[field + '_url'] = None

    return render(request, 'blog/editor.html', {
        'post': post,
        'blocks_json': json.dumps(blocks),
        'all_tags': all_tags,
        'sidebar_posts': _sidebar_posts(),
    })


# ─── API endpoints (staff only) ───────────────────────────────────────────────

@require_POST
@user_passes_test(is_staff, login_url='/login/')
def api_save_post(request):
    try:
        data    = json.loads(request.body)
        post_id = data.get('id')
        title   = data.get('title', '').strip() or 'Untitled'
        excerpt = data.get('excerpt', '').strip()
        status  = data.get('status', 'draft')
        tag_names = [t.strip() for t in data.get('tags', []) if t.strip()]
        seo_title = data.get('seo_title', '').strip()
        seo_desc  = data.get('seo_description', '').strip()
        blocks_data = data.get('blocks', [])

        # Get or create post
        if post_id:
            post = get_object_or_404(Post, id=post_id)
        else:
            post = Post()

        post.title          = title
        post.excerpt        = excerpt
        post.status         = status
        post.seo_title      = seo_title
        post.seo_description = seo_desc

        # Cover image — save path if provided
        cover_path = data.get('cover_path', '').strip()
        if cover_path:
            post.cover_image = cover_path
        elif cover_path == '' and post.pk:
            # explicitly cleared
            post.cover_image = None

        if not post.slug:
            base = slugify(title)
            slug = base
            n = 1
            while Post.objects.filter(slug=slug).exclude(pk=post.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            post.slug = slug

        post.save()

        # Tags
        post.tags.clear()
        for name in tag_names:
            tag, _ = Tag.objects.get_or_create(name=name, defaults={'slug': slugify(name)})
            post.tags.add(tag)

        # Blocks — delete removed ones, upsert rest
        incoming_ids = {b['id'] for b in blocks_data if b.get('id')}
        post.blocks.exclude(id__in=incoming_ids).delete()

        for i, b in enumerate(blocks_data):
            btype = b.get('type', 'text')
            if b.get('id'):
                block = ContentBlock.objects.get(id=b['id'], post=post)
            else:
                block = ContentBlock(post=post, block_type=btype)

            block.position     = i
            block.block_type   = btype
            block.caption      = b.get('caption', '')
            block.image_layout = b.get('image_layout', 'full')

            if btype == 'text':
                block.text_content = b.get('text_content', '')

            block.save()

        return JsonResponse({'ok': True, 'id': post.id, 'slug': post.slug})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)


@require_POST
@user_passes_test(is_staff, login_url='/login/')
def api_delete_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    post.delete()
    return JsonResponse({'ok': True})


@require_POST
@user_passes_test(is_staff, login_url='/login/')
def api_upload_cover(request):
    file    = request.FILES.get('file')
    post_id = request.POST.get('post_id', '')
    if not file:
        return JsonResponse({'ok': False, 'error': 'No file'}, status=400)
    from django.core.files.storage import default_storage
    from django.core.files.base import ContentFile
    import uuid
    ext      = os.path.splitext(file.name)[1].lower()
    filename = f"covers/{uuid.uuid4().hex}{ext}"
    saved    = default_storage.save(filename, ContentFile(file.read()))
    from django.conf import settings
    url = settings.MEDIA_URL + saved
    if post_id:
        try:
            post = Post.objects.get(id=post_id)
            post.cover_image = saved
            post.save(update_fields=['cover_image'])
        except Post.DoesNotExist:
            pass
    return JsonResponse({'ok': True, 'url': url, 'path': saved})


@require_POST
@user_passes_test(is_staff, login_url='/login/')
def api_upload_media(request):
    file     = request.FILES.get('file')
    field    = request.POST.get('field', 'image')   # image / video / audio
    block_id = request.POST.get('block_id', '')      # may be empty for new blocks

    if not file:
        return JsonResponse({'ok': False, 'error': 'No file'}, status=400)

    # Save to a temporary ContentBlock or update existing
    if block_id:
        try:
            block = ContentBlock.objects.get(id=block_id)
        except ContentBlock.DoesNotExist:
            block = None
    else:
        block = None

    # We'll just save to disk directly and return the URL
    from django.core.files.storage import default_storage
    from django.core.files.base import ContentFile
    import uuid

    ext      = os.path.splitext(file.name)[1].lower()
    folder   = {'image': 'blocks/images', 'video': 'blocks/videos', 'audio': 'blocks/audio'}.get(field, 'blocks/misc')
    filename = f"{folder}/{uuid.uuid4().hex}{ext}"
    saved    = default_storage.save(filename, ContentFile(file.read()))

    from django.conf import settings
    url = settings.MEDIA_URL + saved

    # If block exists update the field
    if block:
        if field == 'image':
            block.image = saved
        elif field == 'video':
            block.video = saved
        elif field == 'audio':
            block.audio = saved
        block.save()

    return JsonResponse({'ok': True, 'url': url, 'path': saved})


# ─── Comment + Reaction ───────────────────────────────────────────────────────

@require_POST
def add_comment(request, slug):
    post = get_object_or_404(Post, slug=slug, status='published')
    name = request.POST.get('name', '').strip()
    body = request.POST.get('body', '').strip()
    if name and body:
        Comment.objects.create(post=post, name=name, body=body)
        messages.success(request, 'Sizning xabaringiz muvaffaqiyatli yuborildi!')
    else:
        messages.error(request, 'Iltimos ism va xabarni kiriting.')
    return redirect('blog:post_detail', slug=slug)


@require_POST
def react(request, slug):
    post  = get_object_or_404(Post, slug=slug, status='published')
    emoji = request.POST.get('emoji', '')
    if emoji not in [e[0] for e in EMOJI_CHOICES]:
        return JsonResponse({'error': 'invalid'}, status=400)

    if not request.session.session_key:
        request.session.create()
    session_key = request.session.session_key

    try:
        existing = Reaction.objects.get(post=post, session_key=session_key)
        if existing.emoji == emoji:
            existing.delete()
            active_emoji = None
        else:
            existing.emoji = emoji
            existing.save()
            active_emoji = emoji
    except Reaction.DoesNotExist:
        Reaction.objects.create(post=post, session_key=session_key, emoji=emoji)
        active_emoji = emoji

    return JsonResponse({'active_emoji': active_emoji, 'counts': post.reaction_summary})


# ── Fikrbot AI Chat (Groq) ──────────────────────────────────────────────────
@csrf_exempt
@require_POST
def api_chat(request):
    from django.conf import settings

    try:
        body = json.loads(request.body)
        user_message = body.get('message', '').strip()
        history = body.get('history', [])
    except Exception:
        return JsonResponse({'error': 'Invalid request'}, status=400)

    if not user_message:
        return JsonResponse({'error': 'Empty message'}, status=400)

    api_key = settings.GROQ_API_KEY
    if not api_key:
        return JsonResponse({'error': 'API key not configured'}, status=500)

    # Fetch recent published posts for context
    posts = Post.objects.filter(status='published').order_by('-created_at')[:8]
    post_context = ""
    for p in posts:
        for b in p.blocks.filter(block_type='text')[:1]:
            clean = re.sub(r'<[^>]+>', '', b.text_content or '')[:300]
            post_context += f"- {p.title}: {clean}\n"

    system_prompt = f"""Siz Asilbek Abdurahmonov blogining AI yordamchisisiz — ismi Fikrbot.

Asilbek Abdurahmonov — hayot, ish, o'qish, oila va shaxsiy rivojlanish haqidagi shaxsiy blog.

Vazifangiz:
- Hayot, ish, o'qish, oila, munosabatlar bo'yicha aqlli va samimiy maslahat berish
- Blog postlari haqida savollarga javob berish
- O'zbek va ingliz tilida muloqot qilish (foydalanuvchi qaysi tilda yozsa, shu tilda javob bering)
- Aqlli do'st kabi samimiy va professional bo'ling

Blog postlari:
{post_context}

Qisqa, aniq va foydali javob bering."""

    chat_messages = [{"role": "system", "content": system_prompt}]
    for msg in history[-10:]:
        chat_messages.append({"role": msg.get('role', 'user'), "content": msg.get('content', '')})
    chat_messages.append({"role": "user", "content": user_message})

    try:
        cmd = [
            'curl', '-s', '-X', 'POST',
            'https://api.groq.com/openai/v1/chat/completions',
            '-H', 'Content-Type: application/json',
            '-H', f'Authorization: Bearer {api_key}',
            '-d', json.dumps({
                "model": "llama-3.3-70b-versatile",
                "messages": chat_messages,
                "temperature": 0.8,
                "max_tokens": 1024,
            })
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        data = json.loads(result.stdout)
        if 'error' in data:
            return JsonResponse({'error': f'Groq error: {data["error"]["message"]}'}, status=500)
        reply = data['choices'][0]['message']['content']
        return JsonResponse({'reply': reply})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
