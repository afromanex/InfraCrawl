import importlib

MODULES = [
    'infracrawl.db.engine',
    'infracrawl.db.models',
    'infracrawl.db.metadata',
    'infracrawl.repository.pages',
    'infracrawl.repository.links',
    'infracrawl.repository.configs',
]

def test_imports():
    for m in MODULES:
        importlib.import_module(m)
