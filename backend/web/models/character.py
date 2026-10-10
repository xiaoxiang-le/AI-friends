import uuid

from django.db import models
from django.utils.timezone import now, localtime

from web.models.user import UserProfile


def photo_upload_to(instance, filename):
    ext = filename.split('.')[-1]
    filename = f'{uuid.uuid4().hex[:10]}.{ext}'
    return f'character/photos/{instance.author.user_id}_{filename}'


def background_image_upload_to(instance, filename):
    ext = filename.split('.')[-1]
    filename = f'{uuid.uuid4().hex[:10]}.{ext}'
    return f'character/background_images/{instance.author.user_id}_{filename}'


class Voice(models.Model):
    owner = models.ForeignKey(UserProfile, on_delete=models.CASCADE, null=True, blank=True)
    kind = models.CharField(max_length=10, default='preset')
    status = models.CharField(max_length=12, default='ready')
    target_model = models.CharField(max_length=100, blank=True)
    error = models.CharField(max_length=200, blank=True)
    name = models.CharField(max_length=100)
    voice_id = models.CharField(max_length=100)
    create_time = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.name} - {self.voice_id} - {localtime(self.create_time).strftime('%Y-%m-%d %H:%M:%S')}"


class Character(models.Model):
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    photo = models.ImageField(upload_to=photo_upload_to)
    voice = models.ForeignKey(Voice, default=None, on_delete=models.SET_NULL, blank=True, null=True)
    profile = models.TextField(max_length=100000)
    public_description = models.TextField(max_length=200, blank=True)
    persona_prompt = models.TextField(max_length=100000, blank=True)
    visibility = models.CharField(max_length=10, default='public', choices=[('private', '仅自己'), ('unlisted', '不在发现页展示'), ('public', '公开')])
    status = models.CharField(max_length=12, default='published', choices=[('draft', '草稿'), ('reviewing', '待审核'), ('rejected', '审核拒绝'), ('published', '已发布'), ('archived', '已归档')])
    version = models.PositiveIntegerField(default=1)
    archived_at = models.DateTimeField(null=True, blank=True)
    moderation_reason = models.CharField(max_length=500, blank=True)
    background_image = models.ImageField(upload_to=background_image_upload_to)
    create_time = models.DateTimeField(default=now)
    update_time = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.author.user.username} - {self.name} - {localtime(self.create_time).strftime('%Y-%m-%d %H:%M:%S')}"
