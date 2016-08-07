import uorm as orm
import json

class WebAppRating(orm.Entity):
    app_id = orm.String(index=True, unique=True)
    app_name = orm.String(unique=True)
    rating = orm.Json()
    
