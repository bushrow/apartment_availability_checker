#!/Users/bushrow/.pyenv/versions/3.10.2/bin/python3

import re
import time
from datetime import datetime as dt, timedelta as td
from typing import Any

import bs4
from bs4 import BeautifulSoup
import requests

from apartment_check.util import (
    generate_notification_content,
    read_last_checked_units,
    write_last_checked_units,
)

ALL_FLOORPLAN_URL = "https://ellewestave.com/floorplans/"
SINGLE_FLOORPLAN_URL = "https://ellewestave.com/floorplans/{floorplan}/?forcecache=1"


def check_current_listings_elle_west(
    min_beds,
    min_baths,
    min_sq_ft,
    tgt_date,
    prev_check_filepath: str | tuple[str, str],
    s3_client: Any = None,
) -> str | None:
    available_floorplans: dict[str, dict] = get_floorplan_availability(
        min_beds, min_baths, min_sq_ft
    )
    unit_dicts: list[dict] = get_unit_availability(
        available_floorplans, target_date=tgt_date
    )
    current_units: set = set(unit_dict["unit"] for unit_dict in unit_dicts)
    new_listings: set
    removed_listings: set
    new_listings, removed_listings = diff_units(
        current_units, prev_check_filepath=prev_check_filepath, s3_client=s3_client
    )
    if (len(new_listings) > 0) or (len(removed_listings) > 0):
        content_str: str = generate_notification_content(
            unit_dicts, new_listings, removed_listings
        )
    else:
        content_str = None

    write_last_checked_units_elle(
        current_units, prev_check_filepath, s3_client=s3_client
    )
    return content_str


def get_unit_availability(
    available_floorplans: dict[str, dict], target_date: str, request_delay: int = 1
) -> list[dict]:
    units: list = []
    for ix, fp_tuple in enumerate(available_floorplans.items(), 1):
        fp, fp_info = fp_tuple
        fp_avail_r = requests.get(SINGLE_FLOORPLAN_URL.format(floorplan=fp))
        fp_avail_soup = BeautifulSoup(fp_avail_r.content, "html.parser")

        availability_table = fp_avail_soup.find(
            "table", attrs={"class": "check-availability__table"}
        )
        for tr in availability_table.find_all("tr"):
            unit_cell = tr.find("td", attrs={"class": "check-availability__cell--unit"})
            if unit_cell is None:
                continue
            unit = unit_cell.text.strip()
            unit = re.search("\d{4}", unit).group()
            availability = tr.find(
                "td", attrs={"class": "check-availability__cell--availability"}
            ).text.strip()
            available_now = availability.lower() == "available now"
            if available_now:
                availability = dt.today().strftime("%b %d, %Y")
            availability_dt = min(
                dt.strptime(availability, "%b %d, %Y") + td(days=13),
                dt.strptime(target_date, "%Y-%m-%d"),
            )
            href = tr.find("a", attrs={"class": "check-availability__cell-link"}).attrs[
                "href"
            ]
            link = "https://ellewestave.com" + href.format(
                date=availability_dt.strftime("%m/%d/%Y")
            )
            units.append(
                {
                    "unit": unit,
                    "available_text": (
                        "now" if available_now else availability_dt.strftime("%m/%d/%Y")
                    ),
                    "available_dt": availability_dt.strftime("%m/%d/%Y"),
                    "floorplan": fp,
                    **fp_info,
                    "url": link,
                }
            )
        if ix < len(available_floorplans):
            time.sleep(request_delay)
    return units


def get_floorplan_availability(
    min_beds: float = 0.0, min_baths: float = 0.0, min_sq_ft: float = 0.0
) -> dict[str, dict]:
    r = requests.get(ALL_FLOORPLAN_URL)
    if r.status_code != 200:
        raise RuntimeError("Unable to load floorplans.")
    floorplan_soup = BeautifulSoup(r.content, "html.parser")

    listings = floorplan_soup.find_all(
        "div", attrs={"class": "floorplan-listing__content"}
    )
    available_floorplans = {}
    for listing in listings:
        floorplan_name = listing.find(
            "p", attrs={"class": "floorplan-listing__title"}
        ).text.strip()
        floorplan_price = listing.find(
            "p", attrs={"class": "floorplan-listing__info--price"}
        ).span.text
        if floorplan_price.lower() == "contact us":
            continue
        listing_info = listing.find(
            "p", attrs={"class": "floorplan-listing__info--wrap"}
        )
        listing_info_items = tuple(
            [
                child.text.lower().strip()
                for child in listing_info.children
                if isinstance(child, bs4.element.Tag)
            ]
        )
        if len(listing_info_items) != 3:
            print(
                f"Incorrect number of listing info elements found for floorplan {floorplan_name}."
            )
            continue
        bed_ct, bath_ct, sq_ft = listing_info_items
        bed_ct_re = re.match("^(\d(?:\.5)?) bed$", bed_ct, flags=re.IGNORECASE)
        bath_ct_re = re.match("^(\d(?:\.5)?) bath$", bath_ct, flags=re.IGNORECASE)
        sq_ft_re = re.match(
            "^((?:\d,?)?\d{3}) sq\.? ft\.?$", sq_ft, flags=re.IGNORECASE
        )
        bed_ct_num = float(bed_ct_re.group(1)) if bed_ct_re else None
        bath_ct_num = float(bath_ct_re.group(1)) if bath_ct_re else None
        sq_ft_num = float(sq_ft_re.group(1)) if sq_ft_re else None
        if (
            ((bed_ct_num is not None) and (bed_ct_num < min_beds))
            or ((bath_ct_num is not None) and (bath_ct_num < min_baths))
            or ((sq_ft_num is not None) and (sq_ft_num < min_sq_ft))
        ):
            continue
        available_floorplans[floorplan_name] = {
            "beds": bed_ct_num,
            "baths": bath_ct_num,
            "sq_ft": sq_ft_num,
        }
    return available_floorplans


def diff_units(
    current_units: set[str], prev_check_filepath: str | tuple, s3_client: Any = None
) -> tuple[set, set]:
    prev_units: set = read_last_checked_units_elle(
        prev_check_filepath, s3_client=s3_client
    )
    new_listings: set = current_units.difference(prev_units)
    removed_listings: set = prev_units.difference(current_units)
    return new_listings, removed_listings


def read_last_checked_units_elle(
    prev_check_filepath: str | tuple, s3_client: Any = None
) -> set:
    units_dict = read_last_checked_units(prev_check_filepath, s3_client=s3_client)
    return set(units_dict.get("elle_west_ave", []))


def write_last_checked_units_elle(
    current_units: set, prev_check_filepath: str | tuple, s3_client: Any = None
) -> None:
    units_dict = read_last_checked_units(prev_check_filepath, s3_client=s3_client)
    units_dict["elle_west_ave"] = list(current_units)
    write_last_checked_units(
        prev_check_filepath=prev_check_filepath,
        units_dict=units_dict,
        s3_client=s3_client,
    )
