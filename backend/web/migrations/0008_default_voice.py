from django.db import migrations


def add_default_voice(apps, schema_editor):
    Voice = apps.get_model('web', 'Voice')
    if not Voice.objects.exists():
        Voice.objects.create(name='默认音色', voice_id='longanyang')


class Migration(migrations.Migration):
    dependencies = [('web', '0007_voice_and_systemprompt_align')]
    operations = [migrations.RunPython(add_default_voice, migrations.RunPython.noop)]
