# contract_templates/__init__.py
from flask import Blueprint

contract_templates_bp = Blueprint(
    "contract_templates",
    __name__,
    url_prefix="/drepturi-contract",
)

from . import routes
