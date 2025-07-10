import os
import pytest
from flask import Flask
from dapytains.app.app import create_app
from dapytains.app.ingest import store_catalog
from dapytains.metadata.xml_parser import parse
import uritemplate
import urllib

basedir = os.path.abspath(os.path.dirname(__file__))
BASE_URI = "http://localhost:5000"


@pytest.fixture
def app():
    """Fixture to create a new instance of the Flask app for testing."""
    app = Flask(__name__)
    app, db = create_app(app, base_uri=BASE_URI)
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
        '@context': 'https://distributed-text-services.github.io/specifications/context/1-alpha1.json',
        '@id': 'http://localhost//',
        '@type': 'EntryPoint',
        'dtsVersion': '1-alpha',
        'collection': 'http://localhost:5000/collection/{?id}{&nav}',
        'document': 'http://localhost:5000/document/{?resource}{&ref,start,end,tree}',
        'navigation': 'http://localhost:5000/navigation/{?resource}{&ref,start,end,tree,down}',
    }


def test_collection(client):
    response = client.get('/')
    template = uritemplate.URITemplate(response.get_json()["collection"].replace(BASE_URI, ""))
    response = client.get(template.expand({}))
    j = response.get_json()
    assert {
               '@context': 'https://distributed-text-services.github.io/specifications/context/1-alpha1.json',
               '@id': 'https://foo.bar/default',
               '@type': 'Collection',
               'collection': 'http://localhost:5000/collection/?id=https%3A%2F%2Ffoo.bar%2Fdefault{&nav}',
               'dtsVersion': '1-alpha',
               'dublinCore': {'abstract': ['This is a perfect example of an absract.',
                                           {'lang': 'fr',
                                            'value': 'Et je peux traduire en français'}]},
               'member': [{'@id': 'https://example.org/collection1',
                           '@type': 'Collection',
                           'collection': 'http://localhost:5000/collection/?id=https%3A%2F%2Fexample.org%2Fcollection1{&nav}',
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
                           'collection': 'http://localhost:5000/collection/?id=https%3A%2F%2Fexample.org%2Fresource1{&nav}',
                           'description': 'A document about historical events.',
                           'document': 'http://localhost:5000/document/?resource=https%3A%2F%2Fexample.org'
                                       '%2Fresource1{&ref,start,end,tree}',
                           'dublinCore': {'language': ['en'], 'subject': ['World War II']},
                           'extensions': {'https://example.org/commentcomment': ['Very '
                                                                                 'informative '
                                                                                 'document.'],
                                          'https://example.org/ratingrating': ['5 stars']},
                           'navigation': 'http://localhost:5000/navigation/?resource=https%3A%2F%2Fexample.org'
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
                           'collection': 'http://localhost:5000/collection/?id=https%3A%2F%2Ffoo.bar%2Ftext{&nav}',
                           'description': 'With a description',
                           'document': 'http://localhost:5000/document/?resource=https%3A%2F%2Ffoo.bar%2Ftext{&ref,'
                                       'start,end,tree}',
                           'dublinCore': {'title': ['A simple resource']},
                           'extensions': {'https://foaf.com/foafsomething': ['Truc']},
                           'navigation': 'http://localhost:5000/navigation/?resource=https%3A%2F%2Ffoo.bar%2Ftext{'
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
    assert {'@context': 'https://distributed-text-services.github.io/specifications/context/1-alpha1.json',
            '@id': 'https://example.org/collection1',
            '@type': 'Collection',
            'collection': 'http://localhost:5000/collection/?id=https%3A%2F%2Fexample.org%2Fcollection1{&nav}',
            'dtsVersion': '1-alpha',
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
                        'collection': 'http://localhost:5000/collection/?id=https%3A%2F%2Fexample.org%2Fresource1{&nav}',
                        'description': 'A document about historical events.',
                        'document': 'http://localhost:5000/document/?resource=https%3A%2F%2Fexample.org%2Fresource1{'
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
                        'navigation': 'http://localhost:5000/navigation/?resource=https%3A%2F%2Fexample.org'
                                      '%2Fresource1{&ref,start,end,tree,down}',
                        'title': 'Historical Document',
                        'totalChildren': 0,
                        'totalParents': 2}],
            'title': 'My First Collection',
            'totalChildren': 1,
            'totalParents': 1} == response.get_json()
