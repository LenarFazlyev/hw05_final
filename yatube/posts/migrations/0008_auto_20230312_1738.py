# Generated by Django 2.2.16 on 2023-03-12 14:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0007_follow'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='follow',
            options={'verbose_name': 'Подписки', 'verbose_name_plural': 'Подписки'},
        ),
    ]
