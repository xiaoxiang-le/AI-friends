from django.db import models
from django.utils.timezone import now
from web.models.user import UserProfile
from web.models.character import Character
from web.models.friend import Friend


class GenerationLease(models.Model):
    friend = models.OneToOneField(Friend, on_delete=models.CASCADE)
    request_id = models.CharField(max_length=64)
    cancelled = models.BooleanField(default=False)
    expires_at = models.DateTimeField()


class KnowledgeDocument(models.Model):
    owner = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    character = models.ForeignKey(Character, on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    sha256 = models.CharField(max_length=64)
    content = models.TextField()
    status = models.CharField(max_length=12, default='uploaded')
    error = models.CharField(max_length=200, blank=True)
    index_mode = models.CharField(max_length=20, default='keyword')
    embedding_model = models.CharField(max_length=100, blank=True)
    create_time = models.DateTimeField(default=now)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['character', 'sha256'], name='unique_character_document')]


class KnowledgeChunk(models.Model):
    document = models.ForeignKey(KnowledgeDocument, on_delete=models.CASCADE, related_name='chunks')
    position = models.PositiveIntegerField()
    content = models.TextField()
    vector = models.JSONField(default=list, blank=True)


class ServiceObservation(models.Model):
    service = models.CharField(max_length=20)
    success = models.BooleanField()
    create_time = models.DateTimeField(default=now)


class WorkerHeartbeat(models.Model):
    name = models.CharField(max_length=50, unique=True)
    updated_at = models.DateTimeField(default=now)


class BackgroundJob(models.Model):
    owner = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    kind = models.CharField(max_length=20)
    object_id = models.PositiveIntegerField()
    payload = models.JSONField(default=dict)
    dedupe_key = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=12, default='queued')
    attempts = models.PositiveIntegerField(default=0)
    error = models.CharField(max_length=200, blank=True)
    available_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(default=now)
    create_time = models.DateTimeField(default=now)


class Report(models.Model):
    reporter = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    character = models.ForeignKey(Character, on_delete=models.CASCADE)
    reason = models.CharField(max_length=200)
    status = models.CharField(max_length=12, default='pending', choices=[('pending', '待处理'), ('resolved', '已处理'), ('rejected', '不成立')])
    resolution = models.CharField(max_length=500, blank=True)
    create_time = models.DateTimeField(default=now)


class AuditLog(models.Model):
    actor = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50)
    object_id = models.PositiveIntegerField()
    detail = models.CharField(max_length=200, blank=True)
    create_time = models.DateTimeField(default=now)
