from typing import Dict, List, Optional, Any
from dapitains.app.database import Collection, Navigation, db
from dapitains.metadata.xml_parser import Catalog
from dapitains.tei.document import Document

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

    for index in path:
        try:
            current_level = current_level[index]
            if 'members' in current_level:
                current_level = current_level['members']
        except (IndexError, KeyError):
            return None

    return current_level


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