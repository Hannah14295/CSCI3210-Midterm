from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("races", "0011_race_next_race")]
    operations = [migrations.AddField(model_name="raceparticipant", name="is_ready", field=models.BooleanField(default=False))]
