import os
import pytest
from flask import Flask
from dapytains.app.app import create_app
from dapytains.app.ingest import store_catalog
from dapytains.metadata.xml_parser import parse
import uritemplate
import urllib

basedir = os.path.abspath(os.path.dirname(__file__))
STANDOFF_RESOURCE = "https://foo.bar/standoff"
BASE_URI = "http://localhost"
CONTEXT_URL = "https://dtsapi.org/context/v1.0.json"
DTS_VERSION = "1.0"


@pytest.fixture
def app():
    """Fixture to create a new instance of the Flask app for testing."""
    app = Flask(__name__)
    app, db = create_app(app)
    db_path = os.path.join(basedir, 'app.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()
        catalog, _ = parse(f"{basedir}/catalog/example-collection.xml")
        store_catalog(catalog)

    yield app

    # Teardown: Drop all tables after each test
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Fixture to create a test client for the Flask app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Fixture to create a test CLI runner for the Flask app."""
    return app.test_cli_runner()


def test_index(client):
    """Test the index route."""
    response = client.get('/')
    assert response.status_code == 200
    assert response.get_json() == {
        '@context': CONTEXT_URL,
        '@id': 'http://localhost/',
        '@type': 'EntryPoint',
        'dtsVersion': DTS_VERSION,
        'collection': 'http://localhost/collection/{?id}{&nav}',
        'document': 'http://localhost/document/{?resource}{&ref,start,end,tree}',
        'navigation': 'http://localhost/navigation/{?resource}{&ref,start,end,tree,down}',
    }


def test_collection(client):
    response = client.get('/')
    template = uritemplate.URITemplate(response.get_json()["collection"].replace(BASE_URI, ""))
    response = client.get(template.expand({}))
    j = response.get_json()
    assert {
               '@context': CONTEXT_URL,
               '@id': 'https://foo.bar/default',
               '@type': 'Collection',
               'collection': 'http://localhost/collection/?id=https%3A%2F%2Ffoo.bar%2Fdefault{&nav}',
               'dtsVersion': DTS_VERSION,
               'dublinCore': {'abstract': ['This is a perfect example of an absract.',
                                           {'lang': 'fr',
                                            'value': 'Et je peux traduire en français'}]},
               'member': [{'@id': 'https://example.org/collection1',
                           '@type': 'Collection',
                           'collection': 'http://localhost/collection/?id=https%3A%2F%2Fexample.org%2Fcollection1{&nav}',
                           'dublinCore': {'creator': ['John Doe'],
                                          'date': ['2023-08-24'],
                                          'subject': ['History']},
                           'title': 'My First Collection',
                           'totalChildren': 1,
                           'totalParents': 1},
                          {'@id': 'https://example.org/resource1',
                           '@type': 'Resource',
                           'citationTrees': [{'@type': 'CitationTree',
                                              'citeType': 'book',
                                              'identifier': 'nums'},
                                             {'@type': 'CitationTree',
                                              'citeType': 'book',
                                              'identifier': 'alpha'}],
                           'collection': 'http://localhost/collection/?id=https%3A%2F%2Fexample.org%2Fresource1{&nav}',
                           'description': 'A document about historical events.',
                           'document': 'http://localhost/document/?resource=https%3A%2F%2Fexample.org'
                                       '%2Fresource1{&ref,start,end,tree}',
                           'dublinCore': {'language': ['en'], 'subject': ['World War II']},
                           'extensions': {'https://example.org/commentcomment': ['Very '
                                                                                 'informative '
                                                                                 'document.'],
                                          'https://example.org/ratingrating': ['5 stars']},
                           'navigation': 'http://localhost/navigation/?resource=https%3A%2F%2Fexample.org'
                                         '%2Fresource1{&ref,start,end,tree,down}',
                           'title': 'Historical Document',
                           'totalChildren': 0,
                           'totalParents': 2},
                          {'@id': 'https://foo.bar/text',
                           '@type': 'Resource',
                           'citationTrees': [{'@type': 'CitationTree',
                                              'citeStructure': [{'citeStructure': [{'citeType': 'verse'},
                                                                                   {'citeType': 'bloup'}],
                                                                 'citeType': 'chapter'}],
                                              'citeType': 'book',
                                              'identifier': 'default'}],
                           'collection': 'http://localhost/collection/?id=https%3A%2F%2Ffoo.bar%2Ftext{&nav}',
                           'description': 'With a description',
                           'document': 'http://localhost/document/?resource=https%3A%2F%2Ffoo.bar%2Ftext{&ref,'
                                       'start,end,tree}',
                           'dublinCore': {'title': ['A simple resource']},
                           'extensions': {'https://foaf.com/foafsomething': ['Truc']},
                           'navigation': 'http://localhost/navigation/?resource=https%3A%2F%2Ffoo.bar%2Ftext{'
                                         '&ref,start,end,tree,down}',
                           'title': 'A simple resource',
                           'totalChildren': 0,
                           'totalParents': 1}],
               'title': 'A collection',
               'totalChildren': 3,
               'totalParents': 0} == j
    assert uritemplate.URITemplate(j["member"][0]["collection"]).expand(
        {"id": j["member"][0]["@id"]}) == f"{BASE_URI}/collection/?id={urllib.parse.quote_plus(j['member'][0]['@id'])}"
    collection = uritemplate.URITemplate(j["member"][0]["collection"]).expand(
        {"id": j["member"][0]["@id"]})
    response = client.get(collection.replace(BASE_URI, ""))
    assert {'@context': CONTEXT_URL,
            '@id': 'https://example.org/collection1',
            '@type': 'Collection',
            'collection': 'http://localhost/collection/?id=https%3A%2F%2Fexample.org%2Fcollection1{&nav}',
            'dtsVersion': DTS_VERSION,
            'dublinCore': {'creator': ['John Doe'],
                           'date': ['2023-08-24'],
                           'subject': ['History']},
            'member': [{'@id': 'https://example.org/resource1',
                        '@type': 'Resource',
                        'citationTrees': [{'@type': 'CitationTree',
                                           'citeType': 'book',
                                           'identifier': 'nums'},
                                          {'@type': 'CitationTree',
                                           'citeType': 'book',
                                           'identifier': 'alpha'}],
                        'collection': 'http://localhost/collection/?id=https%3A%2F%2Fexample.org%2Fresource1{&nav}',
                        'description': 'A document about historical events.',
                        'document': 'http://localhost/document/?resource=https%3A%2F%2Fexample.org%2Fresource1{'
                                    '&ref,start,end,tree}',
                        'dublinCore': {'language': ['en'], 'subject': ['World War II']},
                        'extensions': {
                            'https://example.org/commentcomment': [
                                'Very informative document.',
                            ],
                            'https://example.org/ratingrating': [
                                '5 stars',
                            ],
                        },
                        'navigation': 'http://localhost/navigation/?resource=https%3A%2F%2Fexample.org'
                                      '%2Fresource1{&ref,start,end,tree,down}',
                        'title': 'Historical Document',
                        'totalChildren': 0,
                        'totalParents': 2}],
            'title': 'My First Collection',
            'totalChildren': 1,
            'totalParents': 1} == response.get_json()


# ── document endpoint fixtures ────────────────────────────────────────────────

def _make_standoff_app(include_header=False, include_standoff=False):
    flask_app = Flask(__name__)
    flask_app, db = create_app(flask_app, include_header=include_header,
                               include_standoff=include_standoff)
    db_path = os.path.join(basedir, 'app_standoff.db')
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    flask_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(flask_app)
    with flask_app.app_context():
        db.create_all()
        catalog, _ = parse(f"{basedir}/catalog/standoff-catalog.xml")
        store_catalog(catalog)
    return flask_app, db


@pytest.fixture
def standoff_client_default():
    """Document endpoint with both flags off (default behaviour)."""
    flask_app, db = _make_standoff_app(include_header=False, include_standoff=False)
    yield flask_app.test_client()
    with flask_app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def standoff_client_header():
    """Document endpoint with include_header=True only."""
    flask_app, db = _make_standoff_app(include_header=True, include_standoff=False)
    yield flask_app.test_client()
    with flask_app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def standoff_client_standoff():
    """Document endpoint with include_standoff=True only."""
    flask_app, db = _make_standoff_app(include_header=False, include_standoff=True)
    yield flask_app.test_client()
    with flask_app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def standoff_client_both():
    """Document endpoint with both include_header=True and include_standoff=True."""
    flask_app, db = _make_standoff_app(include_header=True, include_standoff=True)
    yield flask_app.test_client()
    with flask_app.app_context():
        db.session.remove()
        db.drop_all()


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_doc(client, ref):
    from urllib.parse import quote_plus
    return client.get(f"/document/?resource={quote_plus(STANDOFF_RESOURCE)}&ref={ref}")


# ── document endpoint tests ───────────────────────────────────────────────────

def test_document_default_no_header_no_standoff(standoff_client_default):
    """By default neither teiHeader nor standOff appears in the response."""
    response = _get_doc(standoff_client_default, "1")
    assert response.status_code == 200
    body = response.data.decode()
    assert "<teiHeader" not in body
    assert "<standOff" not in body
    # passage content is still there
    assert 'xml:id="w1"' in body


def test_document_include_header(standoff_client_header):
    """include_header=True causes teiHeader to appear before text in the response."""
    response = _get_doc(standoff_client_header, "1")
    assert response.status_code == 200
    body = response.data.decode()
    assert "<teiHeader" in body
    assert "<standOff" not in body
    assert body.index("<teiHeader") < body.index("<text")


def test_document_include_standoff(standoff_client_standoff):
    """include_standoff=True filters standOff entries for the retrieved passage.

    div n="1" references LATL, LBHM, MLK (case 1); its word tokens w1–w3
    are targeted by ann1–ann3 (case 2); those spans carry @ana="#pos-NNP"
    pulling in pos-NNP transitively (case 3).  LDAL, JFK, ann4, and pos-JJ
    are excluded because they are only referenced from div n="2".
    """
    response = _get_doc(standoff_client_standoff, "1")
    assert response.status_code == 200
    body = response.data.decode()

    assert "<teiHeader" not in body
    assert "<standOff" in body

    # case 1: passage → standOff
    assert 'xml:id="LATL"' in body
    assert 'xml:id="LBHM"' in body
    assert 'xml:id="MLK"' in body
    assert 'xml:id="LDAL"' not in body
    assert 'xml:id="JFK"' not in body

    # case 2: standOff → passage
    assert 'target="#w1"' in body
    assert 'target="#w2"' in body
    assert 'target="#w3"' in body
    assert 'target="#w7"' not in body

    # case 3: transitive standOff → standOff
    assert 'xml:id="pos-NNP"' in body
    assert 'xml:id="pos-JJ"' not in body

    assert body.index("<text") < body.index("<standOff")


def test_document_include_header_and_standoff(standoff_client_both):
    """With both flags the response order is teiHeader → text → standOff."""
    response = _get_doc(standoff_client_both, "1")
    assert response.status_code == 200
    body = response.data.decode()
    assert "<teiHeader" in body
    assert "<standOff" in body
    assert body.index("<teiHeader") < body.index("<text") < body.index("<standOff")
