import json


def allow_cors(
        content_type="application/json",
        origin="*",
        headers=None,
        methods=None
):
    headers = list(headers) if headers else []
    methods = list(methods) if methods else ['GET']

    if "Content-Type" not in headers: headers.append("Content-Type")
    if "OPTIONS" not in methods: methods.append("OPTIONS")
    if "HEAD" not in methods: methods.append("HEAD")

    allowed_headers = ",".join(headers)
    allowed_methods = ",".join(methods)

    def decorator(func):
        def wrapper(event, context):
            response: dict = func(event, context)

            if not isinstance(response, dict) or "statusCode" not in response:
                response = {
                    "statusCode": 200,
                    "body": json.dumps(response)
                }

            if "headers" not in response:
                response["headers"] = {}

            response["headers"].update({
                "Content-Type": content_type,
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Headers": allowed_headers,
                "Access-Control-Allow-Methods": allowed_methods
            })

            return response

        return wrapper

    return decorator


def allow_cors_auth(
        content_type="application/json",
        origin="*",
        methods=None,
): return allow_cors(
    content_type=content_type, origin=origin, methods=methods,
    headers=["X-Amz-Date", "Authorization", "X-Api-Key", "X-Amz-Security-Token"],
)

allows_cors = allow_cors()
allows_cors_auth = allow_cors_auth()

