from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("viewflow", "0014_alter_process_parent_task"),
    ]

    operations = [
        migrations.AddField(
            model_name="process",
            name="version",
            field=models.PositiveIntegerField(default=1, verbose_name="Version"),
        ),
    ]