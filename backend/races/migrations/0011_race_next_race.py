from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("races", "0010_raceparticipant_typing_started_at")]

    operations = [migrations.AddField(
        model_name="race", name="next_race",
        field=models.OneToOneField(
            to="races.race", related_name="previous_race", null=True, blank=True,
            on_delete=django.db.models.deletion.SET_NULL,
        ),
    )]
