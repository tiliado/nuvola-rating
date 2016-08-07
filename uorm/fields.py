import json

class ValidationError(Exception):
    @classmethod
    def wrong_type(cls, field, expected_types, received):
        if isinstance(expected_types, (tuple, list)):
            expected = "('%s')" % "', '".join(str(t) for t in expected_types)
        else:
            expected = type(expected)
        received = type(received)
        return ValidationError("The '%s' field must be of type %s but '%s' received." % (name, expected, received))


class Field(object):
    def __init__(self, default=None, index=False, unique=False, asc=True, required=True, empty=False,
    primary=False, autoincrement=False):
        self.default = default
        self.index = index
        self.unique = unique
        self.asc = asc
        self.required = required
        self.empty = empty
        self.primary = primary
        self.autoincrement = autoincrement
        self.name = None
    
    def validate(self, value):
        """Validate Python value before it is set."""
    
    def validate_types(self, value, *types):
        if not isinstance(value, types):
            raise ValidationError.wrong_type(self.name, types, value)
    
    def deserialize(self, value):
        """De-serialize database value to Python value."""
        return value
    
    def serialize(self, value):
        """Serialize Python value to database value."""
        return value


class String(Field):
    def validate(self, value):
        self.validate_types(value, str)

    def serialize(self, value):
        assert isinstance(value, str)
        return value
        
    def deserialize(self, value):
        assert isinstance(value, str)
        return value

class Blob(Field):
    def __init__(self, **kwargs):
        super().__init__(index=False, primary=False, unique=False, **kwargs)
    
    def validate(self, value):
        self.validate_types(value, bytes)

class Json(Blob):
    def validate(self, value):
        self.validate_types(value, list, tuple, dict)

    def serialize(self, value):
        return json.dumps(value).encode("utf-8")
        
    def deserialize(self, value):
        return json.loads(value.decode("utf-8") if isinstance(value, bytes) else value)
