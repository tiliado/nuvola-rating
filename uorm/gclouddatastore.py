from .default import set_default_db
from gcloud import datastore

def connect(data_store, namespace=None):
    set_default_db(Connection(data_store, namespace))


class Connection:
    def __init__(self, project, namespace=None):
        self.project = project
        self.namespace = namespace
        self.client = datastore.Client(project=project, namespace=namespace)
    
    def create_key(self, entity_class, entity_id=None):
        entity_kind = entity_class.__name__
        if entity_id:
            return self.client.key(entity_kind, int(entity_id))
        return self.client.key(entity_kind)
    
    def save(self, entity):
        data = entity._as_data()
        print("Save entity: %s" % data)
        key = self.create_key(entity.__class__, data.get("_id"))
        ds_entity = datastore.Entity(key=key, exclude_from_indexes=[])
        ds_entity.update(data)
        self.client.put(ds_entity)
        entity._id = key.id
    
    def query(self, entity_class, offset=None, limit=None, order_by=None):
        pass
    
    def get_keys_for(self, kind, **query):
        kwargs = {
            "kind": kind.__name__,
            
        }
        order_by = query.get("order_by")
        if order_by:
            kwargs["order"] = order_by
        filter_by = query.get("filter_by")
        if filter_by:
            kwargs["filters"] = filter_by
        
        q = self.client.query(**kwargs)
        q.keys_only()
        return (entry.key for entry in q.fetch())
    
    def exec_query(self, query):
        kwargs = {
            "kind": query.kind.__name__,
            
        }
        if query.order_by:
            kwargs["order"] = query.order_by
        if query.filter_by:
            kwargs["filters"] = query.filter_by
        q = self.client.query(**kwargs)
        return Result(query.kind, q.fetch(offset=query.offset, limit=query.limit))
    
    def delete_by_key(self, keys):
        return self.client.delete_multi(keys)
        
    def delete(self, kind, entity_id):
        return self.client.delete(self.create_key(kind, entity_id))
    
    def delete_by(self, kind, **kwargs):
        filter_by = [(key, "=", value) for key, value in kwargs.items()]
        keys = self.get_keys_for(kind, filter_by=filter_by)
        keys = list(keys)
        print(keys)
        return self.delete_by_key(keys)
        
class Result:
    def __init__(self, kind, dataset):
        self.kind = kind
        self.dataset = iter(dataset)
    
    def __iter__(self):
        return self
    
    def __next__(self):
        entry = next(self.dataset)
        entry["_id"] = entry.key.id
        entity = self.kind._from_data(entry)
        return entity
        


    
    
