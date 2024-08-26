from typing import Dict, Any, Optional

from sqlalchemy.orm.collections import collection

from tests.test_db_create import test_navigation

try:
    import uritemplate
    from flask import Flask, request, Response
    from flask_sqlalchemy import SQLAlchemy
    import click
except ImportError:
    print("This part of the package can only be imported with the web requirements.")
    raise

import json

from dapitains.app.database import db, Collection, Navigation
from dapitains.app.ingest import get_nav


def msg_4xx(string, code=404) -> Response:
    return Response(json.dumps({"message": string}), status=code, mimetype="application/json")


def collection_view(identifier: Optional[str], nav: str, templates: Dict[str, str]) -> Response:
    if not identifier:
        coll: Collection = db.session.query(Collection).filter(~Collection.parents.any()).first()
    else:
        coll = Collection.query.where(Collection.identifier==identifier).first()
    if coll is None:
        return msg_4xx("Unknown collection")
    out = coll.json()

    if nav == 'children':
        related_collections = db.session.query(Collection).filter(
            Collection.parents.any(id=coll.id)
        ).all()
    elif nav == 'parents':
        related_collections = db.session.query(Collection).filter(
            Collection.children.any(id=coll.id)
        ).all()
    else:
        return msg_4xx(f"nav parameter has a wrong value {nav}", code=400)

    return Response(json.dumps({
        "@context": "https://distributed-text-services.github.io/specifications/context/1-alpha1.json",
        "dtsVersion": "1-alpha",
        **out,
        "totalParents": coll.total_parents,
        "totalChildren": coll.total_children,
        "member": [
            related.json()
            for related in related_collections
        ]
    }), mimetype="application/json", status=200)


def navigation_view(resource, ref, start, end, tree, down, templates: Dict[str, str]) -> Response:
    if not resource:
        return msg_4xx("Resource parameter was not provided")

    collection: Collection = Collection.query.where(Collection.identifier == resource).first()
    if not collection:
        return msg_4xx(f"Unknown resource `{resource}`")

    nav: Navigation = Navigation.query.where(Navigation.collection_id == collection.id).first()
    if nav is None:
        return msg_4xx(f"The resource `{resource}` does not support navigation")

    # Check for forbidden combinations
    if ref or start or end:
        if tree not in nav.references:
            return msg_4xx(f"Unknown tree {tree} for resource `{resource}`")
        elif ref and (start or end):
            return msg_4xx(f"You cannot provide a ref parameter as well as start or end", code=400)
        elif not ref and ((start and not end) or (end and not start)):
            return msg_4xx(f"Range is missing one of its parameters (start or end)", code=400)
    else:
        if down is None:
            return msg_4xx(f"The down query parameter is required when requesting without ref or start/end", code=400)

    refs = nav.references[tree]
    paths = nav.paths[tree]
    members, start, end = get_nav(refs=refs, paths=paths, start_or_ref=start or ref, end=end, down=down)
    return Response(json.dumps({
        "@context": "https://distributed-text-services.github.io/specifications/context/1-alpha1.json",
        "dtsVersion": "1-alpha",
        "@type": "Navigation",
        "@id": "https://example.org/api/dts/navigation/?resource=https://en.wikisource.org/wiki/Dracula&down=1",
        "resource": collection.json(inject=templates),  # To Do: implement and inject URI templates
        "member": members
    }), mimetype="application/json", status=200)


def create_app(
        app: Flask,
        use_query: bool = False
) -> (Flask, SQLAlchemy):
    """

    Initialisation of the DB is up to you
    """
    navigation_template = uritemplate.URITemplate("/navigation/{?resource}{&ref,start,end,tree,down}")
    collection_template = uritemplate.URITemplate("/navigation/collection/{?id,nav}")
    document_template = uritemplate.URITemplate("/document/{?resource}{&ref,start,end,tree}")

    @app.route("/collection/")
    def collection_route():
        resource = request.args.get("id")
        nav = request.args.get("nav")

        return collection_view(resource, nav, templates={
            "navigation": navigation_template.partial({"resource": resource}).uri,
            "collection": collection_template.partial({"id": resource}).uri,
            "document": document_template.partial({"resource": resource}).uri,
        })

    @app.route("/navigation/")
    def navigation_route():
        resource = request.args.get("resource")
        ref = request.args.get("ref")
        start = request.args.get("start")
        end = request.args.get("end")
        tree = request.args.get("tree")
        down = request.args.get("down", type=int, default=None)

        return navigation_view(resource, ref, start, end, tree, down, templates={
            "navigation": navigation_template.partial({"resource": resource}).uri,
            "collection": collection_template.partial({"id": resource}).uri,
            "document": document_template.partial({"resource": resource}).uri,
        })

    return app, db


if __name__ == "__main__":
    import os
    from dapitains.app.ingest import store_catalog
    from dapitains.metadata.xml_parser import ingest_catalog

    app = Flask(__name__)
    _, db = create_app(app)

    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'app.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    with app.app_context():
        db.drop_all()
        db.create_all()

        catalog, _ = ingest_catalog(f"{basedir}/../../tests/catalog/example-collection.xml")
        store_catalog(catalog)

    app.run()
