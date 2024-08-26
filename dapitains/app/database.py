try:
    from flask_sqlalchemy import SQLAlchemy
    from sqlalchemy.ext.mutable import MutableDict, Mutable
    from sqlalchemy.types import TypeDecorator, TEXT
    from sqlalchemy import func
    import click
except ImportError:
    print("This part of the package can only be imported with the web requirements.")
    raise

from typing import Optional, Dict, Any
import dapitains.metadata.classes as abstracts
from dapitains.metadata.xml_parser import Catalog
from dapitains.tei.document import Document
import json


class CustomKeyJSONDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        # Only convert 'None' string keys back to None
        return {None if k == 'null' else k: v for k, v in obj.items()}

db = SQLAlchemy()

parent_child_association = db.Table('parent_child_association',
    db.Column('parent_id', db.Integer, db.ForeignKey('collections.id'), primary_key=True),
    db.Column('child_id', db.Integer, db.ForeignKey('collections.id'), primary_key=True)
)


class JSONEncoded(TypeDecorator):
    """Enables JSON storage by encoding and decoding on the fly."""
    impl = TEXT

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        else:
            return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.loads(value, cls=CustomKeyJSONDecoder)


class Collection(db.Model):
    __tablename__ = 'collections'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    identifier = db.Column(db.String, nullable=False, unique=True)
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=True)
    resource = db.Column(db.Boolean, default=False)
    filepath = db.Column(db.String, nullable=True)
    dublin_core = db.Column(JSONEncoded, nullable=True)
    extensions = db.Column(JSONEncoded, nullable=True)

    # One-to-one relationship with Navigation
    navigation = db.relationship('Navigation', uselist=False, backref='collection', lazy=True)

    parents = db.relationship(
        'Collection',
        secondary=parent_child_association,
        primaryjoin=id == parent_child_association.c.child_id,
        secondaryjoin=id == parent_child_association.c.parent_id,
        backref='children'
    )

    @property
    def total_children(self):
        return db.session.query(func.count(parent_child_association.c.child_id)).filter(
            parent_child_association.c.parent_id == self.id
        ).scalar()

    @property
    def total_parents(self):
        return db.session.query(func.count(parent_child_association.c.parent_id)).filter(
            parent_child_association.c.child_id == self.id
        ).scalar()

    def json(self, inject: Optional[Dict[str, Any]] = None):
        data = {
            "@type": "Resource" if self.resource else "Collection",
            "@id": self.identifier,
            "title": self.title,
            **(inject or {})
        }
        if self.description:
            data["description"] = self.description
        if self.dublin_core:
            data["dublinCore"] = self.dublin_core
        if self.extensions:
            data["extensions"] = self.extensions

        return data

    @classmethod
    def from_class(cls, obj: abstracts.Collection) -> "Collection":
        return cls(
            identifier=obj.identifier,
            title=obj.title,
            description=obj.description,
            resource=obj.resource,
            filepath=obj.filepath,
            # We are dumping because it's not read or accessible
            dublin_core=[dub.json() for dub in obj.dublin_core],
            extensions=[ext.json() for ext in obj.extension]
        )


class Navigation(db.Model):
    __tablename__ = 'navigations'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, nullable=False)
    collection_id = db.Column(db.Integer, db.ForeignKey('collections.id'), nullable=False, unique=True)
    # default_tree = db.Column(db.String, nullable=True)

    # JSON fields stored as TEXT
    paths = db.Column(JSONEncoded, nullable=False, default={})
    references = db.Column(JSONEncoded, nullable=False, default={})
