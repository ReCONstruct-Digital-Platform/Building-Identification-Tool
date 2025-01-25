from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("buildings", "0005_user_knowledge_level"),
    ]

    operations = [
        migrations.RunSQL(
            """
                CREATE or replace FUNCTION jsonb_to_int_array(jsonb) RETURNS int[] AS $f$
                --- We cast from JSON null to SQL null here to avodi crashes when querying null integers
                SELECT coalesce(array_agg(nullif(x, 'null'))::int[], 
                    CASE WHEN $1 is null THEN null ELSE ARRAY[]::int[] END)
                FROM jsonb_array_elements($1) t(x);
                $f$ LANGUAGE sql IMMUTABLE;

                CREATE or replace FUNCTION jsonb_to_text_array(jsonb) RETURNS text[] AS $f$
                SELECT coalesce(array_agg(x)::text[], 
                    CASE WHEN $1 is null THEN null ELSE ARRAY[]::text[] END)
                FROM jsonb_array_elements_text($1) t(x);
                $f$ LANGUAGE sql IMMUTABLE;
            """,
            """
            drop function jsonb_to_int_array;
            drop function jsonb_to_text_array;
            """,
        )
    ]
