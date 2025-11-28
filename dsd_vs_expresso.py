from DSD.parser import read_file
from DSD.download import Dsd_Download
from utils import parse_date
from typing import Tuple, Dict
from googleads import ad_manager
from line_item_details_in_gam import get_line_items_details_by_name
from dotenv import load_dotenv
from gamPlacements import placement_names
import os

load_dotenv()
NEW_GAM = os.getenv("NEW_GAM")

client = ad_manager.AdManagerClient.LoadFromStorage(NEW_GAM)


def clean_line_item_name(name: str) -> str:
    while len(name) >= 5 and not name[-5:].isdigit():
        name = name[:-1]
    return name


def normalize_geo_list(geo_value):
    """Convert a string or list of geos into a clean list of strings."""
    if isinstance(geo_value, str):
        return [g.strip() for g in geo_value.split(",") if g.strip()]
    elif isinstance(geo_value, list):
        return [g.strip() if isinstance(g, str) else g for g in geo_value]
    return []


def normalize_list(value):
    """Ensure value is always a list of stripped strings."""
    if isinstance(value, str):
        return [value.strip()]
    elif isinstance(value, list):
        return [str(v).strip() for v in value]
    return []


def dsd_vs_expresso(line_item_name: str) -> Tuple[Dict, int]:
    """
    Compare DSD Excel data vs Expresso GAM data for a given line item name.
    Returns (result_dict, status_code)
    """
    line_item_name = input("Enter Parent Line Item Name: ")
    Dsd_Download(line_item_name[:6])
    line_item_name = clean_line_item_name(line_item_name)
    gam_data = get_line_items_details_by_name(client=client, line_item_name=line_item_name)

    dsd_data = read_file(line_item_name)

    if not dsd_data:
        return {"message": "Unable to read DSD data"}, 400

    ad_server = str(dsd_data.get("Ad Server", "")).strip().lower()
    if "double click" not in ad_server or not dsd_data.get("Parent_LI_Name"):
        return {"message": "Invalid Ad Server or missing Parent_LI_Name"}, 400

    matched, unmatched = {}, {}

    # Normalize DSD placements (from placement_names)
    dsd_placements_list = normalize_list(placement_names)

    # --- Loop through GAM data ---
    for g in gam_data:

        g_name = g.get("name", "Unknown Line Item")

        # Normalize GAM placements
        gam_placement = g.get("targetedPlacement")
        gam_placements_list = normalize_list(gam_placement)

        # --- Compare scalar fields ---
        checks = {
            "cpd_daily_rate": (g.get("cpd_daily_rate"), dsd_data.get("Rate")),
            "currency_code": (g.get("currency_code"), dsd_data.get("Currency")),
            "start_date": (parse_date(g.get("start_date")), parse_date(dsd_data.get("Start_Date"))),
            "end_date": (parse_date(g.get("end_date")), parse_date(dsd_data.get("End_Date"))),
        }

        for field, (g_val, d_val) in checks.items():
            if g_val == d_val:
                matched[field] = {"gam": g_val, "dsd": d_val}
            else:
                unmatched.setdefault(field, {"gam": g_val, "dsd": d_val, "unmatch_line_item": []})
                if g_name not in unmatched[field]["unmatch_line_item"]:
                    unmatched[field]["unmatch_line_item"].append(g_name)

        # --- Compare targetedPlacement properly ---
        gam_missing = [v for v in gam_placements_list if v not in dsd_placements_list]
        dsd_missing = [v for v in dsd_placements_list if v not in gam_placements_list]

        if not gam_missing and not dsd_missing:
            matched["targetedPlacement"] = {
                "gam": gam_placements_list,
                "dsd": dsd_placements_list
            }
        else:
            unmatched.setdefault(
                "targetedPlacement",
                {
                    "gam_missing": gam_missing,
                    "dsd_missing": dsd_missing,
                    "unmatch_line_item": []
                }
            )
            if g_name not in unmatched["targetedPlacement"]["unmatch_line_item"]:
                unmatched["targetedPlacement"]["unmatch_line_item"].append(g_name)

        # --- Compare GEO & EXCLUDED_GEO lists ---
        list_fields = [
            ("included_geo", g.get("geo"), dsd_data.get("Geo_Target")),
            ("excluded_geo", g.get("excluded_geo"), dsd_data.get("Geo_Exclusion")),
        ]

        for field_name, gam_val, dsd_val in list_fields:
            gam_list = normalize_geo_list(gam_val)
            dsd_list = normalize_geo_list(dsd_val)

            gam_missing = [v for v in gam_list if v not in dsd_list]
            dsd_missing = [v for v in dsd_list if v not in gam_list]

            if not gam_missing and not dsd_missing:
                matched[field_name] = {"gam": gam_list, "dsd": dsd_list}
            else:
                unmatched.setdefault(
                    field_name,
                    {
                        "gam_missing": gam_missing,
                        "dsd_missing": dsd_missing,
                        "unmatch_line_item": []
                    },
                )
                if g_name not in unmatched[field_name]["unmatch_line_item"]:
                    unmatched[field_name]["unmatch_line_item"].append(g_name)

    print("\nMatched Fields:\n", unmatched)
  

    return {"matched_fields": matched, "unmatched_fields": unmatched}, 200



#dsd_vs_expresso("27651110DOMEINTERATILBOTHINALLCPMVERNEWSSTDBANFY23TILSTANDARDBANNERPKG215107")

#dsd_vs_expresso(line_item_name="286248180DOMEWPPTILBOTHINATFCPDTLGSMYMSOVFY24RTILMRECPPDPKG218529")

dsd_vs_expresso(line_item_name="28983520DOMEPOORVITILBOTHINALLCPMVERNEWSSTDBANFY23TILSTANDARDBANNERPKG219576")