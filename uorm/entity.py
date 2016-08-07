_ID= "_id"
KINDS = []
_EXTRA_DATA = "_extra_data"

from .default import get_default_db
from .fields import Field

class EntityBase:
    def __init__(self, **data):
        self.__dict__[_EXTRA_DATA] = {}
        self._new = True
        self._modified = True
        klass = self.__class__
        for name, value in data.items():
            self.__dict__[name] = value
    
    @classmethod
    def _from_data(klass, data):
        entity = klass()
        entity._load(data)
        return entity
        
    def _load(self, data):
        klass = self.__class__
        for name, value in data.items():
            field = getattr(klass, name)
            self.__dict__[name] = field.deserialize(value)
            
        self._new = False
        self._modified = False
    
    def __getattribute__(self, name):
        val =  object.__getattribute__(self, name)
        if isinstance(val, Field):
            return None
        return val
        
    def __setattr__(self, name, value):
        if name[0] == "_":
            object.__setattr__(self, name, value)
            return
        klass = self.__class__
        field = getattr(klass, name)
        field.validate(value)
        try:
            if self.__dict__[name] != value:
                self.__dict__[name] = value
                self._set_modified(True)
        except KeyError:
            self.__dict__[name] = value
            self._set_modified(True)
    
    def _as_data(self):
        values = self.__dict__
        data = values[_EXTRA_DATA].copy()
        klass = self.__class__
        for name, field in klass._fields:
            try:
                value = values[name]
                data[name] = field.serialize(value) if value is not None else None
            except KeyError:
                data[name] = field.default
        return data
    
    def _set_new(self, value):
        self._new = value
        
    def _set_modified(self, value):
        self._modified = value
    
    def _is_new(self):
        return self._new
        
    def _is_modified(self):
        return self._modified
    
    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, repr(self.__dict__))

class EntityMetaBase(type):
    def __new__(meta, class_name, bases, dct):
        if bases != (EntityBase,):
            fields = []
            for item in dct.items():
                name, field = item
                if isinstance(field, Field):
                    field.name = name
                    fields.append(item)
            dct["_fields"] = fields
            
        return super(EntityMetaBase, meta).__new__(meta, class_name, bases, dct)

class EntityManager:
    def __init__(self, kind):
        self.kind = kind
    
    def all(self):
        return []
    
    def create(self, *, db=None, **data):
        entity = self.kind(**data)
        self.save(entity, db)
        return entity
    
    def save(self, entity, db=None):
        if not db:
            db = get_default_db()
        db.save(entity)
    
    def query(self, _db=None, **kwargs):
        if not _db:
            _db = get_default_db()
        return Query(_db, self.kind, **kwargs)
    
    def get(self, _db=None, **equality_filters):
        filter_by = [(key, "=", value) for key, value in equality_filters.items()]
        return self.query(filter_by=filter_by).one()
    
    def exists(self, _db=None, **equality_filters):
        filter_by = [(key, "=", value) for key, value in equality_filters.items()]
        return self.query(filter_by=filter_by).exists()
        
    def all(self, _db=None):
        return self.query(_db=_db).all()
        
    def delete_by(self, _db=None, **kwargs):
        if not _db:
            _db = get_default_db()
        return _db.delete_by(self.kind, **kwargs)
        

class Query:
    def __init__(self, db, kind, offset=0, limit=None, order_by=None, filter_by=None):
        self.db = db;
        self.kind = kind
        self.offset = offset
        self.limit = limit
        if isinstance(order_by, str):
            order_by = [order_by]
        self.order_by = order_by
        self.filter_by = filter_by
    
    def all(self):
        self.limit = None
        self.offset = 0
        return self.db.exec_query(self)
    
    def one(self):
        self.limit = 1
        result = tuple(self.db.exec_query(self))
        if result:
            return result[0]
        else:
            raise self.kind.DoesNotExist()
    
    def exists(self):
        try:
            self.one()
            return True
        except self.kind.DoesNotExist:
            return False

class DoesNotExistError(Exception):
    def __init__(self, kind):
        super().__init__("Desired entity '%s' doesn't exist." % kind.__name__)

class EntityMeta(EntityMetaBase):
    def __init__(cls, name, bases, dct):
        if bases != (EntityBase,):
            KINDS.append(cls)
        cls.entities = EntityManager(cls)
        class DoesNotExist(DoesNotExistError):
            def __init__(self):
                super().__init__(cls)
        cls.DoesNotExist = DoesNotExist
        super(EntityMeta, cls).__init__(name, bases, dct)

class Entity(EntityBase, metaclass=EntityMeta):
    
    def __init__(self, _id=None, **data):
        try:
            field = getattr(self.__class__, _ID)
            if _id is not None:
                field.validate(_id)
            self.__dict__[_ID] = _id
        except AttributeError:
            self.__dict__[_ID] = _id
        
        super().__init__(**data)
    
    def save(self, db=None):
        self.entities.save(self, db=db)
    
    def _load(self, data):
        try:
            _id = data[_ID]
            del(data[_ID])
            try:
                self.__setattr__(_ID, _id)
            except AttributeError:
                self.__dict__[_ID] = _id
        except KeyError:
            pass
        super()._load(data)
    
    def __setattr__(self, name, value):
        if name == _ID and not hasattr(self.__class__, name):
            if self.__dict__[name] != value:
                self.__dict__[name] = value
                self._set_modified(True)
        else:
            super().__setattr__(name, value)
        
    def _as_data(self):
        data = super()._as_data()
        try:
            _id = data[_ID]
            del(data[_ID])
        except KeyError:
            _id = self.__dict__.get(_ID, None)
        if _id is None:
            if _ID in self.__class__.__dict__:
                raise ValueError("Custom _id field not set.")
        else:
            data[_ID] = _id
        return data


