from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_notification'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='is_read',
            field=models.BooleanField(default=False),
        ),
    ]
