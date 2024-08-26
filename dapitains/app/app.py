from typing import Dict, Any, Optional

from dapitains.tei.document import Document

try:
    import uritemplate
    from flask import Flask, request, Response
    from flask_sqlalchemy import SQLAlchemy
    import click
except ImportError:
    print("This part of the package can only be imported with the web requirements.")
    raise

import json
import lxml.etree as ET
from dapitains.app.database import db, Collection, Navigation
from dapitains.app.navigation import get_nav


def msg_4xx(string, code=404) -> Response:
    return Response(json.dumps({"message": string}), status=code, mimetype="application/json")


def collection_view(
        identifier: Optional[str],
        nav: str,
        templates: Dict[str, uritemplate.URITemplate]
) -> Response:
    """ Builds a collection view, regardless of how the parameters are received

    :param identifier:
    :param nav:
    :param templates:
    """
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
        "collection": templates["collection"].uri,
        "member": [
                related.json(
                    inject=dict(
                        **{
                            "collection": templates["collection"].partial({"id": related.identifier}).uri,
                            "document": templates["document"].partial({"resource": related.identifier}).uri,
                        },
                        **(
                            {
                                "navigation": templates["navigation"].partial({"resource": related.identifier}).uri,
                            } if coll.citeStructure else {}
                        )
                    ) if related.resource else related.json({
                        "collection": templates["collection"].partial({"id": related.identifier}).uri
                    })
                )
                for related in related_collections
            ]
    }), mimetype="application/json", status=200)


def document_view(resource, ref, start, end, tree) -> Response:
    if not resource:
        return msg_4xx("Resource parameter was not provided")

    collection: Collection = Collection.query.where(Collection.identifier == resource).first()
    if not collection:
        return msg_4xx(f"Unknown resource `{resource}`")

    nav: Navigation = Navigation.query.where(Navigation.collection_id == collection.id).first()
    if nav is None:
        return msg_4xx(f"The resource `{resource}` does not support navigation")

    tree = tree or collection.default_tree

    # Check for forbidden combinations
    if ref or start or end:
        if tree not in nav.references:
            return msg_4xx(f"Unknown tree {tree} for resource `{resource}`")
        elif ref and (start or end):
            return msg_4xx(f"You cannot provide a ref parameter as well as start or end", code=400)
        elif not ref and ((start and not end) or (end and not start)):
            return msg_4xx(f"Range is missing one of its parameters (start or end)", code=400)

    paths = nav.paths[tree]
    if start and end and (start not in paths or end not in paths):
        return msg_4xx(f"Unknown reference {start} or {end} in the requested tree.", code=404)
    if ref and ref not in paths:
        return msg_4xx(f"Unknown reference {ref} in the requested tree.", code=404)

    if not ref and not start:
        with open(collection.filepath) as f:
            content = f.read()
        return Response(content, mimetype="application/xml")

    doc = Document(collection.filepath)
    return Response(
        ET.tostring(doc.get_passage(
            ref_or_start=ref or start,
            end=end,
            tree=tree
        ), encoding=str),
        mimetype="application/xml"
    )


def navigation_view(resource, ref, start, end, tree, down, templates: Dict[str, str]) -> Response:
    if not resource:
        return msg_4xx("Resource parameter was not provided")

    collection: Collection = Collection.query.where(Collection.identifier == resource).first()
    if not collection:
        return msg_4xx(f"Unknown resource `{resource}`")

    nav: Navigation = Navigation.query.where(Navigation.collection_id == collection.id).first()
    if nav is None:
        return msg_4xx(f"The resource `{resource}` does not support navigation")

    tree = tree or collection.default_tree

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
        base_uri: str,
        use_query: bool = False
) -> (Flask, SQLAlchemy):
    """

    Initialisation of the DB is up to you
    """
    navigation_template = uritemplate.URITemplate(base_uri+"/navigation/{?resource}{&ref,start,end,tree,down}")
    collection_template = uritemplate.URITemplate(base_uri+"/collection/{?id,nav}")
    document_template = uritemplate.URITemplate(base_uri+"/document/{?resource}{&ref,start,end,tree}")

    @app.route("/")
    def index_route():
        return Response(
            json.dumps({
                "@context": "https://distributed-text-services.github.io/specifications/context/1-alpha1.json",
                "dtsVersion": "1-alpha",
                "@id": f"{request.url_root}{request.path}",
                "@type": "EntryPoint",
                "collection": collection_template.uri,
                "navigation" : navigation_template.uri,
                "document": document_template.uri
            }),
            mimetype="application/json"
        )

    @app.route("/collection/")
    def collection_route():
        resource = request.args.get("id")
        nav = request.args.get("nav", "children")

        return collection_view(resource, nav, templates={
            "navigation": navigation_template,
            "collection": collection_template,
            "document": document_template,
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

    @app.route("/document/")
    def document_route():
        resource = request.args.get("resource")
        ref = request.args.get("ref")
        start = request.args.get("start")
        end = request.args.get("end")
        tree = request.args.get("tree")
        return document_view(resource, ref, start, end, tree)

    return app, db


if __name__ == "__main__":
    import os
    from dapitains.app.ingest import store_catalog
    from dapitains.metadata.xml_parser import parse

    app = Flask(__name__)
    _, db = create_app(app, base_uri="http://localhost:5000")

    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'app.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    with app.app_context():
        db.drop_all()
        db.create_all()

        catalog, _ = parse(f"{basedir}/../../tests/catalog/example-collection.xml")
        store_catalog(catalog)

    app.run()
