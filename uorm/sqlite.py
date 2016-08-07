import threading
import sqlite3

from .default import set_default_db
from .entity import KINDS
from . import fields


DEFAULT_LIMIT = 0x7FFFFFFF
SQL_TYPE_INTEGER = "INTEGER"
SQL_TYPE_BLOB = "BLOB"
SQL_TYPE_TEXT = "TEXT"

SQL_TYPES = (
    (fields.String, SQL_TYPE_TEXT),
    (fields.Blob, SQL_TYPE_BLOB),
)


def connect(db_file, namespace=None):
    set_default_db(Connection(db_file, namespace))


def escape_sql_id(sql):
    return sql.replace("\"", "\"\"");


def dict_factory(cursor, row):
    data = {}
    for index, desc in enumerate(cursor.description):
        data[desc[0]] = row[index]
    return data


class Connection:
    def __init__(self, db_file, namespace=None):
        self.db_file = db_file
        self.namespace = namespace
        self.conn_key = "%s:%s" % (db_file, namespace or "")
        self.create_tables()
    
    def create_tables(self):
        sql = []
        for kind in KINDS:
            sql.append(self.create_table_sql(kind))
        sql = "".join(sql)
        with self.conn as conn:
            print(sql)
            conn.executescript(sql)
    
    def create_table_sql(self, kind):
        table_name = self.table_name(kind)
        sql = ["CREATE TABLE IF NOT EXISTS \"%s\" (" % table_name]
        sql.append("\n {} {} PRIMARY KEY AUTOINCREMENT".format(escape_sql_id("_id"), SQL_TYPE_INTEGER))
        indexes = []
        for i, field_tuple in enumerate(kind._fields):
            name, field = field_tuple
            for field_type, sql_type in SQL_TYPES:
                if isinstance(field, field_type):
                    break
            else:
                sql_type = SQL_TYPE_BLOB
            sql.append(",\n {} {}".format(escape_sql_id(name), sql_type))
            if field.index:
                indexes.append(name)
            if field.unique:
                sql.append(" UNIQUE")
            if not field.empty:
                sql.append(" NOT NULL")
        sql.append("\n);\n")
        for name in indexes:
            sql.append('CREATE INDEX IF NOT EXISTS "{0}_{1}_index" ON "{0}" ("{1}");\n'.format(
                self.table_name(kind), escape_sql_id(name)))
        sql = "".join(sql)
        return sql
    
    @property
    def conn(self):
        local = threading.local()
        connections = getattr(local, "sqlite3connections", None)
        if connections is None:
            local.sqlite3connections = connections = {}
        try:
            return connections[self.conn_key]
        except KeyError:
            connections[self.conn_key] = conn = sqlite3.connect(self.db_file)
            conn.row_factory = dict_factory
            return conn
    
    def table_name(self, kind):
        name = kind.__name__
        if self.namespace:
            name = self.namespace + "_" + name
        return escape_sql_id(name)
    
    def save(self, entity):
        kind = entity.__class__
        data = entity._as_data()
        pk = data.get("_id")
        columns = []
        values = []
        for i, field_tuple in enumerate(kind._fields):
            name, field = field_tuple
            columns.append(escape_sql_id(name))
            values.append(data.get(name))
                
        if pk is None:
            sql = ['INSERT INTO\n "{}"("'.format(self.table_name(kind))]
            sql.append('", "'.join(columns))
            sql.append('")\n VALUES(')
            sql.append(', '.join(('?',) * len(columns)))
            sql.append(');');
            sql = "".join(sql)
            print(">>>", sql, values)
            with self.conn as conn:
                cursor = conn.cursor()
                cursor.execute(sql, values)
                entity._id = cursor.lastrowid
        else:
            sql = ['UPDATE "{}" SET\n '.format(self.table_name(kind))]
            sql.append(', '.join('"{}" = ?'.format(c) for c in columns))
            sql.append('\n WHERE "_id" = ?;')
            sql = "".join(sql)
            values.append(pk)
            print(">>>", sql, values)
            with self.conn as conn:
                conn.execute(sql, values)
    
    def query(self, kind, offset=None, limit=None, order_by=None):
        raise NotImplementedError
    
    def get_keys_for(self, kind, **query):
        cursor = self.conn.cursor()
        table_name = self.table_name(kind)
        sql = ['SELECT "{0}"."{1}" AS "{1}" FROM "{0}"'.format(table_name, escape_sql_id("_id"))]
        bound_values = []
        self.append_query(sql, bound_values, kind, **query)
        sql.append(";")
        sql = "".join(sql)
        print(">>>", sql, bound_values)
        result = cursor.execute(sql, bound_values)
        return (row["_id"] for row in result.fetchall())
    
    def exec_query(self, query):
        kind = query.kind
        cursor = self.conn.cursor()
        table_name = self.table_name(kind)
        sql = ["SELECT "]
        bound_values = []
        
        sql.append(' "{0}"."{1}" AS "{1}"'.format(table_name, escape_sql_id("_id")))
        for i, field_tuple in enumerate(kind._fields):
            field_name, field = field_tuple
            sql.append(",")
            sql.append(" \"{0}\".\"{1}\" AS \"{1}\"".format(table_name, escape_sql_id(field_name)))
        
        sql.append(" FROM \"%s\"" % table_name);
        if query.filter_by:
            sql.append(" WHERE")
            for i, filter_tuple in enumerate(query.filter_by):
                name, operator, value = filter_tuple
                if i != 0:
                    sql.append(" AND")
                sql.append(" \"{0}\".\"{1}\" {2} ?".format(table_name, escape_sql_id(name), operator))
                bound_values.append(value)
        if query.order_by:
            sql.append(" ORDER BY")
            for i, order in enumerate(query.order_by):
                if i != 0:
                    sql.append(",")
                if order[0] == "-":
                    order = order[1:]
                    direction = "DESC"
                else:
                    direction = "ASC"
                sql.append(" \"{0}\".\"{1}\" {2}".format(table_name, escape_sql_id(order), direction))
        
        if query.offset is not None:
            limit = query.limit if query.limit is not None else DEFAULT_LIMIT
            offset = query.offset
            sql.append(" LIMIT {0} OFFSET {1}".format(limit, offset))
        elif query.limit is not None:
            sql.append(" LIMIT {0}".format(query.limit))
        
        sql.append(";")
        sql = "".join(sql)
        print(">>>", sql, bound_values)
        result = cursor.execute(sql, bound_values)
        return Result(query.kind, result)
    
    def append_query(self, sql, bound_values, kind, **query):
        table_name = self.table_name(kind)
        filter_by = query.get("filter_by")
        if filter_by:
            sql.append(" WHERE")
            for i, filter_tuple in enumerate(filter_by):
                name, operator, value = filter_tuple
                if i != 0:
                    sql.append(" AND")
                sql.append(" \"{0}\".\"{1}\" {2} ?".format(table_name, escape_sql_id(name), operator))
                bound_values.append(value)
        
        order_by = query.get("order_by")
        if order_by:
            sql.append(" ORDER BY")
            for i, order in enumerate(query.order_by):
                if i != 0:
                    sql.append(",")
                if order[0] == "-":
                    order = order[1:]
                    direction = "DESC"
                else:
                    direction = "ASC"
                sql.append(" \"{0}\".\"{1}\" {2}".format(table_name, escape_sql_id(order), direction))
        
        offset = query.get("offset")
        if offset is not None:
            limit = query.get("limit", DEFAULT_LIMIT)
            sql.append(" LIMIT {0} OFFSET {1}".format(limit, offset))
        else:
            limit = query.get("limit")
            if limit is not None:
                sql.append(" LIMIT {0}".format(limit))
        
    def delete_by_key(self, kind, keys):
        sql = [
            'DELETE FROM "{0}" WHERE "{0}"."{1}" IN ('.format(self.table_name(kind), escape_sql_id("_id")),
            ', '.join('?' * len(keys)),
            ');'
        ]
        sql = "".join(sql)
        bound_values = keys
        print(">>>", sql, bound_values)
        with self.conn as conn:
            result = conn.execute(sql, bound_values)
            return result
        
    def delete(self, kind, entity_id):
        return self.client.delete(self.create_key(kind, entity_id))
    
    def delete_by(self, kind, **kwargs):
        filter_by = [(key, "=", value) for key, value in kwargs.items()]
        sql = ['DELETE FROM "{0}"'.format(self.table_name(kind))]
        bound_values = []
        self.append_query(sql, bound_values, kind, filter_by=filter_by)
        sql.append(';')
        sql = "".join(sql)
        print(">>>", sql, bound_values)
        with self.conn as conn:
            result = conn.execute(sql, bound_values)
            return result
        
class Result:
    def __init__(self, kind, dataset):
        self.kind = kind
        self.dataset = dataset
    
    def __iter__(self):
        return self
    
    def __next__(self):
        entry = self.dataset.fetchone()
        if entry is None:
            raise StopIteration
        
        entity = self.kind._from_data(entry)
        return entity
