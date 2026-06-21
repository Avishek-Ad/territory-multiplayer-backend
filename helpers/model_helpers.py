from django.utils.text import slugify
import uuid

def generate_room_code(instance):
    name = instance.name
    unique_id = str(uuid.uuid4()).replace("-", "")
    if not name:
        return unique_id
    name_slug = slugify(name)
    short_unique_id = unique_id[:5]
    return f"{name_slug}-{short_unique_id}"