import json
import os

import boto3

from apartment_check.properties import check_current_listings_elle_west
from apartment_check.util import send_notification

BUCKET = "apartment_check_tracking_bucket"
PREV_CHECK_KEY = "last_checked_unit_nums.json"
TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]

s3_client = boto3.client("s3")
sns_client = boto3.client("sns")


def lambda_handler(event: dict, context: dict) -> dict:
    min_beds = float(os.environ["APT_MIN_BEDS"])
    min_baths = float(os.environ["APT_MIN_BATHS"])
    min_sq_ft = float(os.environ["APT_MIN_SQ_FT"])
    tgt_date = os.environ["APT_TGT_DATE"]

    content_str = check_current_listings_elle_west(
        min_beds=min_beds,
        min_baths=min_baths,
        min_sq_ft=min_sq_ft,
        tgt_date=tgt_date,
        prev_check_filepath=(BUCKET, PREV_CHECK_KEY),
        s3_client=s3_client,
    )
    if content_str is not None:
        send_notification(
            sns_client=sns_client,
            message=content_str,
            subject="Change in Available Apartments at Elle West",
            topic_arn=TOPIC_ARN,
        )
    return {
        "status_code": 200,
        "message": json.dumps("Hello World!"),
    }
