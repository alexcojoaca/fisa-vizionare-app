from flask import Blueprint

pdf_viewer_bp = Blueprint("pdf_viewer", __name__, url_prefix="/pdf")

from . import routes
