from flask import Blueprint
routes = Blueprint('routes', __name__)

from .base import *
from .admin import *