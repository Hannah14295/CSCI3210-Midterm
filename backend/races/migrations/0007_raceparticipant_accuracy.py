from decimal import Decimal

from django.db import migrations, models


def backfill_accuracy(apps, schema_editor):
    Participant = apps.get_model("races", "RaceParticipant")
    entries = Participant.objects.using(schema_editor.connection.alias)
    completed = entries.filter(finished_at__isnull=False, wpm__isnull=False)
    for entry in completed.select_related("race").iterator():
        target = entry.race.race_text
        typed = entry.typed_text
        # Historical scores without a full saved passage cannot be reconstructed.
        if not target or len(typed) != len(target):
            continue
        correct = sum(expected == actual for expected, actual in zip(target, typed))
        accuracy = Decimal(str(round(correct / len(typed) * 100, 2)))
        entries.filter(pk=entry.pk).update(accuracy=accuracy)


class Migration(migrations.Migration):
    dependencies = [("races", "0006_raceparticipant_elapsed_seconds_and_more")]

    operations = [
        migrations.AddField(
            model_name="raceparticipant",
            name="accuracy",
            field=models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True),
        ),
        migrations.RunPython(backfill_accuracy, migrations.RunPython.noop),
    ]
