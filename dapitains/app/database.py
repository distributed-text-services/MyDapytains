try:
    from flask_sqlalchemy import SQLAlchemy
    from sqlalchemy.ext.mutable import MutableDict
    from sqlalchemy.types import TypeDecorator, TEXT
    import click
except ImportError:
    print("This part of the package can only be imported with the web requirements.")
    raise

import dapitains.metadata.classes as abstracts
import json

db = SQLAlchemy()

parent_child_association = db.Table('parent_child_association',
    db.Column('parent_id', db.Integer, db.ForeignKey('collections.id'), primary_key=True),
    db.Column('child_id', db.Integer, db.ForeignKey('collections.id'), primary_key=True)
)


class JSONEncodedDict(TypeDecorator):
    """Enables JSON storage by encoding and decoding on the fly."""
    impl = TEXT

    def process_bind_param(self, value, dialect):
        if value is None:
            return ''
        elif isinstance(value, dict):
            return json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return '""'
        return json.loads(value)

class Collection(db.Model):
    __tablename__ = 'collections'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    identifier = db.Column(db.String, nullable=False, unique=True)
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=True)
    resource = db.Column(db.Boolean, default=False)
    filepath = db.Column(db.String, nullable=True)
    dublin_core = db.Column(MutableDict.as_mutable(JSONEncodedDict), nullable=True)
    extensions = db.Column(MutableDict.as_mutable(JSONEncodedDict), nullable=True)

    # One-to-one relationship with Navigation
    navigation = db.relationship('Navigation', uselist=False, backref='collection', lazy='noload')


    parents = db.relationship(
        'Collection',
        secondary=parent_child_association,
        primaryjoin=id == parent_child_association.c.child_id,
        secondaryjoin=id == parent_child_association.c.parent_id,
        backref='children'
    )

    @classmethod
    def from_class(cls, obj: abstracts.Collection) -> "Collection":
        return cls(
            identifier=obj.identifier,
            title=obj.title,
            description=obj.description,
            resource=obj.resource,
            filepath=obj.filepath,
            # We are dumping because it's not read or accessible
            dublin_core=json.dumps([dub.json() for dub in obj.dublin_core]),
            extensions=json.dumps([ext.json() for ext in obj.extension])
        )

class Navigation(db.Model):
    __tablename__ = 'navigations'

    id = db.Column(db.Integer, primary_key=True)
    collection_id = db.Column(db.Integer, db.ForeignKey('collections.id'), nullable=False, unique=True)
    default_tree = db.Column(db.String, nullable=True)

    # JSON fields stored as TEXT
    paths = db.Column(MutableDict.as_mutable(JSONEncodedDict), nullable=False, default={})
    references = db.Column(MutableDict.as_mutable(JSONEncodedDict), nullable=False, default={})

if __name__ == "__main__":
    import flask
    import os
    app = flask.Flask(__name__)

    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'app.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    with app.app_context():
        db.create_all()