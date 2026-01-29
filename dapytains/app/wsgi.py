import os
from dapytains.app.app import app, db
from dapytains.app.ingest import store_catalog
from dapytains.metadata.xml_parser import parse
from dotenv_flow import dotenv_flow

dotenv_flow(os.getenv("SERVER_ENV", "prod"))

if __name__ == "__main__":
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URI", "sqlite:///../app.db")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    with app.app_context():
        db.drop_all()
        db.create_all()

        catalog, _ = parse(os.getenv("DTSCATALOG", "tests/catalog/example-collection.xml"))
        store_catalog(catalog)

    app.run(debug=("prod" != os.getenv("SERVER_ENV", "prod")), host=os.getenv("SERVER_HOST", "0.0.0.0"), port=os.getenv("SERVER_PORT", 5000))
