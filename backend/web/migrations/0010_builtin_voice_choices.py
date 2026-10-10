from django.db import migrations


def add_voice_choices(apps, schema_editor):
    Voice = apps.get_model('web', 'Voice')
    voices = [('longanyang','龙安洋'), ('longxiaochun_v3','龙小淳'),
              ('longxiaoxia_v3','龙小夏'), ('longyumi_v3','YUMI'),
              ('longanyun_v3','龙安昀'), ('longanwen_v3','龙安温'),
              ('longanli_v3','龙安莉')]
    for voice_id, name in voices:
        Voice.objects.using(schema_editor.connection.alias).get_or_create(voice_id=voice_id, defaults={'name':name})
    Voice.objects.using(schema_editor.connection.alias).filter(voice_id='longanyang', name='默认音色').update(name='龙安洋')


class Migration(migrations.Migration):
    dependencies = [('web','0009_friend_memory_version_message_request_id_and_more')]
    # Keep voices referenced by existing characters if the migration is reversed.
    operations = [migrations.RunPython(add_voice_choices, migrations.RunPython.noop)]
