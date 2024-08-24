from typing import Dict, List, Optional, Any, Tuple
from dapitains.app.database import Collection, Navigation, db
from dapitains.metadata.xml_parser import Catalog
from dapitains.tei.document import Document
import copy

def store_catalog(catalog: Catalog):
    for identifier, collection in catalog.objects.items():
        db.session.add(Collection.from_class(collection))
        if collection.resource:
            doc = Document(collection.filepath)
            references = {
                key: struct.find_refs(root=doc.xml, structure=struct.units) for key, struct in doc.citeStructure.items()
            }


def get_member_by_path(data: List[Dict[str, Any]], path: List[int]) -> Optional[Dict[str, Any]]:
    """
    Retrieve the member at the specified path in the nested data structure.

    :param data: The nested data structure (list of dictionaries).
    :param path: A list of indices that represent the path to the desired member.
    :return: The member at the specified path, or None if the path is invalid.
    """
    current_level = data

    path_copy = [] + path
    while path_copy:
        index = path_copy.pop(0)
        try:
            current_level = current_level[index]
            if 'members' in current_level and path_copy:
                current_level = current_level['members']
        except (IndexError, KeyError):
            return None

    return current_level


def strip_members(obj: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in obj.items() if k != "members"}


def generate_paths(data: List[Dict[str, Any]], path: Optional[List[int]] = None) -> Dict[str, List[int]]:
    """
    Generate a dictionary mapping each 'ref' in a nested data structure to its path.

    The path is represented as a list of indices that show how to access each 'ref'
    in the nested structure.

    :param data: The nested data structure (list of dictionaries). Each dictionary
                 can have a 'ref' and/or 'members' key.
    :param path: A list of indices representing the current path in the nested data
                 structure. Used internally for recursion. Defaults to None for the
                 initial call.
    :return: A dictionary where each key is a 'ref' and each value is a list of indices
             representing the path to that 'ref' in the nested structure.
    """
    if path is None:
        path = []

    paths = {}

    def recurse(items, current_path):
        for index, item in enumerate(items):
            ref = item.get('ref')
            if ref:
                # Record the path for the current reference
                paths[ref] = current_path + [index]

            members = item.get('members')
            if members:
                # Recurse into the 'members' list
                recurse(members, current_path + [index])

    recurse(data, [])
    return paths


def get_nav(
        refs: List[Dict[str, Any]],
        paths: Dict[str, List[int]],
        start_or_ref: Optional[str],
        end: Optional[str],
        down: Optional[int] = 1
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:

    paths_index = list(paths.keys())
    start_index, end_index = None, None
    if start_or_ref:
        start_index = paths_index.index(start_or_ref)
    if end:
        end_index = paths_index.index(end) + 1

    paths = dict(list(paths.items())[start_index:end_index])

    current_level = [0]

    start_path, end_path = None, None

    if start_or_ref:
        start_path = paths[start_or_ref]
        current_level.append(len(start_path))
    if end:
        end_path = paths[end]
        current_level.append(len(end_path))

    current_level = max(current_level)

    if down == -1:
        down = max(list(map(len, paths.values())))

    if down == 0:
        paths = {key: value for key, value in paths.items() if len(value) == current_level}
    else:
        paths = {key: value for key, value in paths.items() if current_level < len(value) <= down + current_level}

    return (
        [
            strip_members(get_member_by_path(refs, path)) for path in paths.values()
        ],
        strip_members(get_member_by_path(refs, start_path)) if start_path else None,
        strip_members(get_member_by_path(refs, end_path)) if end_path else None
    )


if __name__ == "__main__":
    import flask
    import os
    from dapitains.metadata.xml_parser import ingest_catalog
    app = flask.Flask(__name__)

    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'app.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    with app.app_context():
        db.drop_all()
        db.create_all()

        catalog, _  = ingest_catalog("/home/thibault/dev/MyDapytains/tests/catalog/example-collection.xml")

        store_catalog(catalog)