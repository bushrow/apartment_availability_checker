import json
from io import StringIO
from typing import Any

from botocore.exceptions import ClientError


def read_last_checked_units(
    prev_check_filepath: str | tuple, s3_client: Any = None
) -> dict[str, list]:
    if isinstance(prev_check_filepath, str):
        try:
            with open(prev_check_filepath, "r") as f:
                prev_units = json.load(f)
        except FileNotFoundError:
            prev_units = {}
    elif isinstance(prev_check_filepath, tuple):
        bucket = prev_check_filepath[0]
        key = prev_check_filepath[1]
        try:
            json_str = (
                s3_client.get_object(Bucket=bucket, Key=key)["Body"]
                .read()
                .decode("utf-8")
            )
            prev_units = json.loads(json_str)
        except ClientError:
            prev_units = {}
    else:
        raise SyntaxError(
            f"Invalid parameter for prev_check_filepath: {prev_check_filepath}"
        )
    return prev_units


def write_last_checked_units(
    prev_check_filepath: str | tuple, units_dict: dict, s3_client: Any = None
) -> None:
    if isinstance(prev_check_filepath, str):
        with open(prev_check_filepath, "w") as f:
            json.dump(units_dict, f)
    elif isinstance(prev_check_filepath, tuple):
        bucket = prev_check_filepath[0]
        key = prev_check_filepath[1]
        buffer = StringIO()
        json.dump(units_dict, buffer)
        buffer.seek(0)
        s3_client.put_object(Bucket=bucket, Key=key, Body=buffer.getvalue())


def generate_notification_content(
    units: list[dict], new_listings: set, removed_listings: set
) -> str | None:
    if len(new_listings.union(removed_listings)) == 0:
        return None
    new_units = (
        "\r\n\r\n".join(
            [
                f"{unit_info['unit']} ({unit_info['floorplan']}): available {unit_info['available_text']}\r\n{unit_info['url']}"
                for unit_info in units
                if unit_info["unit"] in new_listings
            ]
        )
        if new_listings
        else "none"
    )

    removed_units = "\r\n".join(removed_listings) if removed_listings else "none"
    notif_content = (
        f"NEW:\r\n----\r\n{new_units}\r\n\r\nREMOVED:\r\n--------\r\n{removed_units}" ""
    )
    return notif_content


def send_notification(
    sns_client: Any,
    message: str,
    subject: str,
    topic_arn: str,
):
    """Wrapper for SNS Publish API call, to simplify mocking for testing."""
    return sns_client.publish(
        TopicArn=topic_arn,
        Message=message,
        Subject=subject,
    )
