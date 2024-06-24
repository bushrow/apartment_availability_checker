import json


def lambda_handler(event: dict, context: dict) -> dict:
    # implement lambda function code here
    return {
        "status_code": 200,
        "message": json.dumps("Hello World!"),
    }
