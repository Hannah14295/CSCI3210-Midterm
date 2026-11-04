from django.db import migrations


def rename_practice_passage(apps, schema_editor):
    Paragraph = apps.get_model("races", "Paragraph")
    Paragraph.objects.using(schema_editor.connection.alias).filter(
        title__in=["First practice race", "Practice Race"],
    ).update(title="Practice race")


class Migration(migrations.Migration):
    dependencies = [("races", "0008_add_fable_passages")]

    operations = [migrations.RunPython(rename_practice_passage, migrations.RunPython.noop)]
