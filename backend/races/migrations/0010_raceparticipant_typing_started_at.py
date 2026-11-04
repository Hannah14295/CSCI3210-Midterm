from django.db import migrations, models
from django.db.models import OuterRef, Subquery


def preserve_existing_clocks(apps, schema_editor):
    Participant = apps.get_model("races", "RaceParticipant")
    Race = apps.get_model("races", "Race")
    database = schema_editor.connection.alias
    old_start = Race.objects.using(database).filter(pk=OuterRef("race_id")).values("started_at")[:1]
    Participant.objects.using(database).exclude(typed_text="").update(typing_started_at=Subquery(old_start))


class Migration(migrations.Migration):
    dependencies = [("races", "0009_rename_practice_passage")]

    operations = [
        migrations.AddField(
            model_name="raceparticipant", name="typing_started_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.RunPython(preserve_existing_clocks, migrations.RunPython.noop),
    ]
