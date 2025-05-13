from flask import Flask as _Flask
from catalog.models import Catalog

class Flask(_Flask):
    catalog: Catalog
