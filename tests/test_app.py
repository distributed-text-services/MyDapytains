import os
import pytest
from flask import Flask
from dapitains.app.app import create_app
from dapitains.app.ingest import store_catalog
from dapitains.metadata.xml_parser import parse


basedir = os.path.abspath(os.path.dirname(__file__))


@pytest.fixture
def app():
    """Fixture to create a new instance of the Flask app for testing."""
    app = Flask(__name__)
    app, db = create_app(app, base_uri="http://localhost:5000")
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
        'collection': 'http://localhost:5000/collection/{?id,nav}',
        'document': 'http://localhost:5000/document/{?resource}{&ref,start,end,tree}',
        'navigation': 'http://localhost:5000/navigation/{?resource}{&ref,start,end,tree,down}',
    }
