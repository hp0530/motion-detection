from django.urls import path
from .views import detect_motion ,video_feed ,signup ,home ,index ,object_detection
from django.contrib.auth import views as auth_views
from .forms import LoginForm
from django.conf import settings
from django.conf.urls.static import static



urlpatterns = [
    path('detect-motion/', detect_motion, name='detect_motion'),
    path('video-feed/', video_feed, name='video-feed'),
    path('signup/',signup,name='signup'),
    path('home/',home , name='home'),
    path('index/',index,name='index'),
    path('object-detection/',object_detection,name='object_detection'),
    path('login/',auth_views.LoginView.as_view(template_name='login.html',authentication_form=LoginForm),name='login'), 
]+static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

