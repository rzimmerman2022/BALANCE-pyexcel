from pathlib import Path
import yaml
from balance_pipeline.errors import FatalSchemaError

def load_registry(path: Path) -> list[dict]:
    """
    Load the schema registry YAML file from the given path.
    Returns a list of schema definitions.
    Raises FatalSchemaError on file not found, parse errors, or wrong type.
    """
    try:
        text = path.read_text(encoding='utf-8')
    except FileNotFoundError as e:
        raise FatalSchemaError(f"Schema registry file not found: {path}") from e
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise FatalSchemaError(f"Error parsing schema registry YAML {path}: {e}") from e
    if not isinstance(data, list):
        raise FatalSchemaError(f"Schema registry must be a list of schemas; got {type(data)} from {path}")
    return data

def find_matching_schema(
    headers: list[str],
    filename: str,
    registry: list[dict]
) -> dict:
    """
    Find a schema in registry matching the given filename and headers.
    Returns the matching schema dict or raises FatalSchemaError if none match.
    """
    # Normalize header strings
    actual = set(str(h).strip() for h in headers)
    fname = Path(filename).name
    for schema in registry:
        schema_id = schema.get('id', '<unknown>')
        # Match filename pattern
        pattern = schema.get('match_filename')
        if pattern and Path(fname).match(pattern):
            # If header signature defined, require all to be present
            sig = schema.get('header_signature')
            if sig:
                if all(col in actual for col in sig):
                    return schema
            else:
                return schema
    # Fallback: match by header signature only
    for schema in registry:
        sig = schema.get('header_signature')
        if sig and all(col in actual for col in sig):
            return schema
    # No match
    raise FatalSchemaError(f"No matching schema for file '{filename}' with headers {headers}")
