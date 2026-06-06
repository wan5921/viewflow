from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("workflow", "0014_alter_process_parent_task"),
    ]

    operations = [
        migrations.AddField(
            model_name="process",
            name="version",
            field=models.IntegerField(default=1, verbose_name="Version"),
        ),
    ]
