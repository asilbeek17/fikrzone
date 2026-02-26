from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    path('', views.home, name='home'),
    path('search/', views.search, name='search'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('write/', views.editor, name='editor_create'),
    path('write/<slug:slug>/', views.editor, name='editor_edit'),
    path('api/post/save/', views.api_save_post, name='api_save_post'),
    path('api/post/<int:pk>/delete/', views.api_delete_post, name='api_delete_post'),
    path('api/upload/', views.api_upload_media, name='api_upload_media'),
    path('api/upload/cover/', views.api_upload_cover, name='api_upload_cover'),
    path('tag/<slug:slug>/', views.tag_posts, name='tag'),
    path('<slug:slug>/', views.post_detail, name='post_detail'),
    path('<slug:slug>/comment/', views.add_comment, name='add_comment'),
    path('<slug:slug>/react/', views.react, name='react'),
    path('api/chat/', views.api_chat, name='api_chat'),
]
