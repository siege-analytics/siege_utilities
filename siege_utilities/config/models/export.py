"""
Bulk import/export for Person/Actor entity collections.

Provides functions to serialize all entity types (users, clients, collaborators,
organizations, collaborations) to a single YAML document and deserialize back.
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from pathlib import Path

import yaml

from .actor_types import User, Client, Collaborator, Organization, Collaboration
from .person import _convert_to_yaml_safe

# Version of the export format
EXPORT_FORMAT_VERSION = "1.0"


def export_entities(
    users: Optional[List[User]] = None,
    clients: Optional[List[Client]] = None,
    collaborators: Optional[List[Collaborator]] = None,
    organizations: Optional[List[Organization]] = None,
    collaborations: Optional[List[Collaboration]] = None,
    path: Optional[Path] = None,
    exclude_sensitive: bool = False,
) -> str:
    """
    Export all entity types to a single YAML document.

    Args:
        users: List of User instances to export.
        clients: List of Client instances to export.
        collaborators: List of Collaborator instances to export.
        organizations: List of Organization instances to export.
        collaborations: List of Collaboration instances to export.
        path: Optional file path to write the YAML to.
        exclude_sensitive: If True, redact sensitive credential data.

    Returns:
        YAML string of all exported entities.
    """
    document = {
        'version': EXPORT_FORMAT_VERSION,
        'exported_at': datetime.now().isoformat(),
        'entities': {}
    }

    if users:
        document['entities']['users'] = [
            u.to_dict(exclude_sensitive=exclude_sensitive) for u in users
        ]
    if clients:
        document['entities']['clients'] = [
            c.to_dict(exclude_sensitive=exclude_sensitive) for c in clients
        ]
    if collaborators:
        document['entities']['collaborators'] = [
            c.to_dict(exclude_sensitive=exclude_sensitive) for c in collaborators
        ]
    if organizations:
        document['entities']['organizations'] = [
            o.to_dict() for o in organizations
        ]
    if collaborations:
        document['entities']['collaborations'] = [
            c.to_dict() for c in collaborations
        ]

    document = _convert_to_yaml_safe(document)
    yaml_str = yaml.dump(document, default_flow_style=False, sort_keys=False)

    if path is not None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml_str)

    return yaml_str


def import_entities(yaml_str_or_path: Union[str, Path]) -> Dict[str, list]:
    """
    Import entities from a YAML document.

    Args:
        yaml_str_or_path: YAML string or path to a YAML file.

    Returns:
        Dictionary with keys 'users', 'clients', 'collaborators',
        'organizations', 'collaborations', each containing a list of
        the corresponding model instances. Also includes 'version'
        and 'exported_at' metadata.
    """
    source = yaml_str_or_path
    if isinstance(source, Path) or (isinstance(source, str) and '\n' not in source and Path(source).exists()):
        source = Path(source).read_text()
    data = yaml.safe_load(source)

    result: Dict[str, Any] = {
        'version': data.get('version', '1.0'),
        'exported_at': data.get('exported_at'),
        'users': [],
        'clients': [],
        'collaborators': [],
        'organizations': [],
        'collaborations': [],
    }

    entities = data.get('entities', {})

    type_map = {
        'users': User,
        'clients': Client,
        'collaborators': Collaborator,
        'organizations': Organization,
        'collaborations': Collaboration,
    }

    for key, model_cls in type_map.items():
        for item_data in entities.get(key, []):
            result[key].append(model_cls(**item_data))

    return result
