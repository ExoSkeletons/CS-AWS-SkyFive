import decimal
import json

class DynamoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            # If it's a whole number, cast to int; otherwise, float
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DynamoJSONEncoder, self).default(obj)