from typing import Dict, Optional
from dapytains.app.database import Collection, Navigation, db, parent_child_association
from dapytains.app.navigation import generate_paths
from dapytains.metadata.xml_parser import Catalog
from dapytains.tei.document import Document
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
                coll_db.default_tree = doc.default_tree
                db.session.add(coll_db)
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
