
_default_db = None

def set_default_db(db):
    global _default_db
    _default_db = db

def get_default_db():
    return _default_db
