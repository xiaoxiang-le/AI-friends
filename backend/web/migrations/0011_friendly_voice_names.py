from django.db import migrations


def rename_builtin_voices(apps, schema_editor):
    Voice = apps.get_model('web', 'Voice')
    names = {
        'longanyang':'阳光男声',
        'longxiaochun_v3':'知性女声',
        'longxiaoxia_v3':'沉稳女声',
        'longyumi_v3':'青春女声',
        'longanyun_v3':'温柔男声',
        'longanwen_v3':'温柔女声',
        'longanli_v3':'干练女声',
    }
    for voice_id, name in names.items():
        Voice.objects.using(schema_editor.connection.alias).filter(voice_id=voice_id).update(name=name)


class Migration(migrations.Migration):
    dependencies = [('web','0010_builtin_voice_choices')]
    operations = [migrations.RunPython(rename_builtin_voices, migrations.RunPython.noop)]
