from django.contrib import admin
from .models.character import Character, Voice
from .models.friend import Friend, Message, SystemPrompt
from .models.user import UserProfile
from .models.resources import KnowledgeDocument, BackgroundJob, Report, AuditLog

# Register your models here.
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    raw_id_fields = ('user', )


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    raw_id_fields = ('author', 'voice')
    list_display = ('id', 'name', 'author', 'status', 'visibility', 'version')
    list_filter = ('status', 'visibility')
    search_fields = ('name', 'author__user__username')

    def save_model(self, request, obj, form, change):
        if change:
            obj.version += 1
        super().save_model(request, obj, form, change)
        actor = UserProfile.objects.filter(user=request.user).first()
        AuditLog.objects.create(actor=actor, action='admin.character.update', object_id=obj.pk,
            detail=f'{obj.status}/{obj.visibility}')


admin.site.register(Voice)


@admin.register(Friend)
class FriendAdmin(admin.ModelAdmin):
    raw_id_fields = ('me', 'character',)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    raw_id_fields = ('friend', )

admin.site.register(SystemPrompt)


@admin.register(KnowledgeDocument)
class KnowledgeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'owner', 'character', 'status')
    list_filter = ('status',)
    readonly_fields = ('sha256', 'content', 'status', 'error')


@admin.register(BackgroundJob)
class JobAdmin(admin.ModelAdmin):
    list_display = ('id', 'kind', 'object_id', 'status', 'attempts', 'updated_at')
    list_filter = ('status', 'kind')
    readonly_fields = ('kind', 'owner', 'object_id', 'payload', 'dedupe_key', 'status', 'attempts', 'error', 'available_at', 'updated_at', 'create_time')

    def has_add_permission(self, request):
        return False


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'character', 'reporter', 'reason', 'status')
    list_filter = ('status',)
    readonly_fields = ('reporter', 'character', 'reason', 'create_time')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        AuditLog.objects.create(actor=UserProfile.objects.filter(user=request.user).first(),
            action='admin.report.resolve', object_id=obj.pk, detail=obj.status)


@admin.register(AuditLog)
class AuditAdmin(admin.ModelAdmin):
    list_display = ('id', 'actor', 'action', 'object_id', 'create_time')
    readonly_fields = ('actor', 'action', 'object_id', 'detail', 'create_time')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
