from typing import Dict, Set, Callable
import json
import lxml.etree as et
from flask import Response
from .database import Collection
from dataclasses import field
from saxonche import PySaxonProcessor, PyXsltExecutable
from dapytains.processor import get_processor



class Transformer(object):
    def __init__(self, supported_media_types: Set[str] = None):
        self.supported_media_types: Set[str] = supported_media_types or set()

    def transform(self, media: str, collection: Collection, document: et.ElementTree) -> Response:
        if media not in self.supported_media_types:
            return Response(json.dumps({"message": f"Unsupported/invalid media type {media}"}), status=403, mimetype="application/json")



class GeneralisticXSLTransformer(Transformer):
    """ A transformer that applies the same XSL for all file using only the media type for transformation scenario

    :param xslts: A dictionary of STR -> PATH where str is a media type and PATH a path to an xslt
    :param media_type_mapping: (Optional) Provides a query media type string (e.g. json) to a correct mimetype (application/json)
    """
    def __init__(self, xslts: Dict[str, str], media_type_mapping: Dict[str, str] = None):
        super().__init__(supported_media_types=set(xslts.keys()))
        self.xslts = xslts
        self.active_xslts: Dict[str, PyXsltExecutable] = {}
        self.mapping: Dict[str, str] = media_type_mapping or {}
        self.processor = get_processor()
        for key, xsl_path in xslts.items():
            try:
                compiler = self.processor.new_xslt30_processor()
                self.active_xslts[key]  = compiler.compile_stylesheet(stylesheet_file=xsl_path)
            except Exception as e:
                print(f"Error compiling {xsl_path}: {e}")

    def transform(self, media: str, collection: Collection, document: et.ElementTree) -> Response:
        if media not in self.supported_media_types:
            return super().transform(media, collection, document)

        transformer = self.active_xslts[media]
        document_builder = self.processor.new_document_builder()
        return Response(
            transformer.transform_to_string(
                xdm_node=document_builder.parse_xml(xml_text=et.tostring(document, encoding=str))
            ),
            status=200,
            mimetype=self.mapping.get(media, media)
        )
