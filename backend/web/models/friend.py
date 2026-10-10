from django.db import models
from django.utils.timezone import now, localtime

from web.models.character import Character
from web.models.user import UserProfile
from web.services.private_files import private_storage


class Friend(models.Model):
    me = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    character = models.ForeignKey(Character, on_delete=models.CASCADE)
    memory = models.TextField(default="", max_length=5000, blank=True, null=True)
    memory_version = models.PositiveIntegerField(default=0)
    memory_enabled = models.BooleanField(default=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    create_time = models.DateTimeField(default=now)
    update_time = models.DateTimeField(default=now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['me', 'character'], name='unique_user_character_friend')]

    def __str__(self):
        return f"{self.character.name} - {self.me.user.username} - {localtime(self.create_time).strftime('%Y-%m-%d %H:%M:%S')}"


class Message(models.Model):
    friend = models.ForeignKey(Friend, on_delete=models.CASCADE)
    user_message = models.TextField()
    input = models.TextField()
    output = models.TextField()
    request_id = models.CharField(max_length=64, null=True, blank=True)
    status = models.CharField(max_length=12, default='completed')
    error = models.CharField(max_length=200, blank=True)
    sources = models.JSONField(default=list, blank=True)
    audio = models.FileField(upload_to='chat/audio/', storage=private_storage, blank=True)
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    create_time = models.DateTimeField(default=now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['friend', 'request_id'], name='unique_friend_chat_request')]

    def __str__(self):
        return f"{self.friend.character.name} - {self.friend.me.user.username} - {self.user_message[:50]} - {localtime(self.create_time).strftime('%Y-%m-%d %H:%M:%S')}"


class SystemPrompt(models.Model):
    title = models.CharField(max_length=100)
    order_number = models.IntegerField(default=0)
    prompt = models.TextField(max_length=10000)
    create_time = models.DateTimeField(default=now)
    update_time = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.title} - {self.order_number} - {self.prompt[:50]} - {localtime(self.create_time).strftime('%Y-%m-%d %H:%M:%S')}"
