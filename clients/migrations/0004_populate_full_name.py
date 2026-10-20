from django.db import migrations

def populate(apps, schema_editor):
    Client = apps.get_model('clients', 'Client')
    for c in Client.objects.all():
        full = f"{c.first_name} {c.last_name}".strip()
        if full:
            Client.objects.filter(pk=c.pk).update(full_name=full)

class Migration(migrations.Migration):
    dependencies = [
        ('clients', '0003_add_full_name_field'),
    ]
    operations = [
        migrations.RunPython(populate, migrations.RunPython.noop),
    ]