# Generated by Django 5.0.6 on 2024-07-16 18:05

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('blog_generator', '0002_contact_email_alter_contact_message_and_more'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Contact',
        ),
    ]
