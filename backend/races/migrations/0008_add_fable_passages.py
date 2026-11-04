"""Make the bundled fables available in local and hosted databases once."""
from django.db import migrations


FABLES = [('The Dog and His Reflection', 'A dog carried a bone across a bridge. Looking down, he saw his reflection and thought another dog had a bigger bone. He barked to steal it, dropping his own into the river. Wanting more had cost him everything.'), ('The Fox and the Crow', 'A crow sat in a tree with a piece of cheese in her beak. A fox looked up and praised her beautiful feathers. He said that a bird so lovely must have a wonderful voice. Proud of his words, the crow opened her beak to sing. The cheese fell, and the fox caught it. The crow learned that sweet words do not always come from a kind heart.'), ('The Lion and the Mouse', 'A tiny mouse ran over a sleeping lion and woke him. The lion caught her beneath his paw, but she begged him to let her go. One day, she promised, she might help him. The lion laughed at the idea, yet lifted his paw. Days later, hunters trapped the lion in a rope net. His roar brought the mouse running. She chewed through the ropes until he could step free. The lion thanked his little friend, knowing now that kindness could return in the smallest form.'), ('The Tortoise and the Hare', 'The hare liked to boast that no animal could outrun him. Tired of his teasing, the tortoise challenged him to a race. When the fox gave the signal, the hare rushed ahead and soon disappeared around a bend. Seeing no sign of the tortoise, he decided to rest beneath a shady tree. The tortoise kept walking, one slow step after another. He passed the sleeping hare without stopping. At last, the hare woke and raced toward the finish, but the tortoise was already there. The animals cheered for the quiet winner. Speed had given the hare a lead, but patience and steady effort had won the race.'), ('The Ant and the Grasshopper', "All summer, the grasshopper played music in the meadow while the ant carried seeds into her home. He invited her to stop working and enjoy the sunshine. She replied that warm days would not last forever, then returned for another seed. When autumn arrived, the grasshopper still sang, certain he would find food when he needed it. Soon, snow covered the fields, and the meadow grew silent. Hungry and cold, he knocked on the ant's door. She welcomed him inside and shared a bowl of grain. As the wind shook the windows, he promised to gather food before the next winter. In spring, he kept his promise. He worked beside the ant each morning, then filled the warm afternoons with music.")]


def add_fables(apps, schema_editor):
    Paragraph = apps.get_model("races", "Paragraph")
    paragraphs = Paragraph.objects.using(schema_editor.connection.alias)
    for title, text in FABLES:
        # Preserve existing passages, including locally edited versions.
        if not paragraphs.filter(title=title).exists():
            paragraphs.create(title=title, text=text)


class Migration(migrations.Migration):
    dependencies = [("races", "0007_raceparticipant_accuracy")]

    operations = [migrations.RunPython(add_fables, migrations.RunPython.noop)]
