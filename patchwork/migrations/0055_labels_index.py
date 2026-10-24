from django.db import migrations
from django.contrib.postgres.operations import BtreeGinExtension


def create_label_indexes(apps, schema_editor):
    if schema_editor.connection.vendor.startswith('postgres'):
        schema_editor.execute("""
            CREATE INDEX patch_labels_idx ON patchwork_patch
                USING GIN (labels);
        """)
        schema_editor.execute("""
            CREATE INDEX patch_labels_covering_idx ON patchwork_patch
                USING GIN (project_id, archived, state_id, labels);
        """)
    elif schema_editor.connection.vendor.startswith('mysql'):
        schema_editor.execute("""
            CREATE INDEX patch_labels_idx ON patchwork_patch
                ((CAST(labels AS CHAR(25) ARRAY)));
        """)
        schema_editor.execute("""
            CREATE INDEX patch_labels_covering_idx ON patchwork_patch
                (project_id, archived, state_id,
                 (CAST(labels AS CHAR(25) ARRAY)));
        """)


class Migration(migrations.Migration):
    dependencies = [
        ('patchwork', '0054_add_patch_labels'),
    ]

    operations = [
        # runs only on postgres
        BtreeGinExtension(),
        migrations.RunPython(create_label_indexes, atomic=False),
    ]
