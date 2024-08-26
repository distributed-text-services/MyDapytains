from typing import Dict, Optional
from dapitains.app.database import Collection, Navigation, db, parent_child_association
from dapitains.app.navigation import generate_paths
from dapitains.metadata.xml_parser import Catalog
from dapitains.tei.document import Document
import tqdm


def store_single(catalog: Catalog, keys: Optional[Dict[str, int]]):
    keys = keys or {}
    for identifier, collection in tqdm.tqdm(catalog.objects.items(), desc="Parsing all collections"):
        coll_db = Collection.from_class(collection)
        db.session.add(coll_db)
        db.session.flush()
        keys[coll_db.identifier] = coll_db.id
        if collection.resource:
            doc = Document(collection.filepath)
            if doc.citeStructure:
                references = {
                    tree: [ref.json() for ref in obj.find_refs(doc.xml, structure=obj.structure)]
                    for tree, obj in doc.citeStructure.items()
                }
                paths = {key: generate_paths(tree) for key, tree in references.items()}
                nav = Navigation(collection_id=coll_db.id, paths=paths, references=references)
                db.session.add(nav)
                coll_db.citeStructure = {
                    key: value.structure.json()
                    for key, value in doc.citeStructure.items()
                }
        db.session.commit()

    for parent, child in catalog.relationships:
        insert_statement = parent_child_association.insert().values(
            parent_id=keys[parent],
            child_id=keys[child]
        )
        db.session.execute(insert_statement)
    db.session.commit()


def store_catalog(*catalogs):
    keys = {}
    for catalog in catalogs:
        store_single(catalog, keys)


if __name__ == "__main__":
    import flask
    import os
    from dapitains.metadata.xml_parser import parse
    app = flask.Flask(__name__)

    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'app.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    with app.app_context():
        db.drop_all()
        db.create_all()

        catalog, _  = parse("/home/thibault/dev/MyDapytains/tests/catalog/example-collection.xml")

        store_catalog(catalog)
