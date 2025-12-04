from googleads import ad_manager
from dotenv import load_dotenv
import os

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import calendar

load_dotenv()
NEW_GAM = os.environ.get("NEW_GAM")

GAM_MINUTES = {
    "ZERO": 0,
    "FIFTEEN": 15,
    "THIRTY": 30,
    "FORTY_FIVE": 45
}

#---------------------------------------------------------------------------------------------------------------------------------------------
#                           Helper Functions for Daypart Expansion , Placement and AdUnit Names
#---------------------------------------------------------------------------------------------------------------------------------------------
def expand_daypart_to_dates(start_date, end_date, day_parts):
    """
    Given a date range and dayParts, returns a list of all matching date/time runs.
    """
    if not start_date or not end_date:
        return []

    # Initialize sets to collect unique dates and days
    unique_dates = set()
    unique_days = set()

    start_date_dt = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")

    current_date = start_date_dt
    while current_date <= end_date_dt:
        weekday = calendar.day_name[current_date.weekday()].upper()

        for dp in day_parts:
            dp_weekday = dp.get('dayOfWeek')
            if dp_weekday != weekday:
                continue
            start_time = dp.get('startTime', {})
            end_time = dp.get('endTime', {})
            start_hour = start_time.get('hour', 0)
            start_minute = GAM_MINUTES.get(start_time.get('minute', 'ZERO'), 0)
            end_hour = end_time.get('hour', 0)
            end_minute = GAM_MINUTES.get(end_time.get('minute', 'ZERO'), 0)
            unique_dates.add(current_date.strftime("%Y-%m-%d"))
            unique_days.add(dp_weekday)

        current_date += timedelta(days=1)

    dates_list = sorted(list(unique_dates))
    days_list = sorted(list(unique_days))
    return [{
        "dates": dates_list,
        "days": days_list,
        "startTime": f"{start_hour:02d}:{start_minute:02d}",
        "endTime": f"{end_hour:02d}:{end_minute:02d}",
    }]

#--------------------------------------------------------------------------------------------------

def parse_gam_date(date_obj) -> Optional[str]:
    """Convert GAM date object to string YYYY-MM-DD."""
    if date_obj and hasattr(date_obj, 'date'):
        d = date_obj.date
        return f"{d.year:04d}-{d.month:02d}-{d.day:02d}"
    return None

def parse_gam_time(obj) -> Optional[str]:
    
    """Extract time (HH:MM:SS) from GAM date-time object."""
    if obj and hasattr(obj, 'hour') and hasattr(obj, 'minute') and hasattr(obj, 'second'):
        return f"{obj.hour:02d}:{obj.minute:02d}:{obj.second:02d}"


#--------------------------------------------------------------------------------------------------------
def get_placement_and_adunit_names_by_id(client, targetedAdUnits, excludedAdUnits, targetedPlacementIds):
    """
    Retrieves the names of ad units and placements from Google Ad Manager
    using their respective IDs.

    This function fetches:
      - Names of targeted ad units
      - Names of excluded ad units
      - Names of targeted placements

    Args:
        client (ad_manager.AdManagerClient): The authenticated Google Ad Manager API client.
        targetedAdUnits (List[str] or List[int]): List of ad unit IDs to be targeted.
        excludedAdUnits (List[str] or List[int]): List of ad unit IDs to be excluded.
        targetedPlacementIds (List[str] or List[int]): List of placement IDs to be targeted.

    Returns:
        dict: A dictionary containing:
            - 'targetedAdUnits' (List[str]): Names of the targeted ad units.
            - 'excludedAdUnits' (List[str]): Names of the excluded ad units.
            - 'targetedPlacements' (List[str]): Names of the targeted placements.

    Example:
        >>> get_placement_and_adunit_names_by_id(client, [12345], [], [67890])
        {
            'targetedAdUnits': ['Homepage_MREC'],
            'excludedAdUnits': [],
            'targetedPlacements': ['News Section Placement']
        }
    """
    inventory_service = client.GetService('InventoryService', version='v202411')
    placement_service = client.GetService('PlacementService', version='v202411')

    def fetch_ad_unit_names(ids):
        if not ids:
            return []
        id_list = ', '.join(str(i) for i in ids)
        statement = {
            'query': f'WHERE id IN ({id_list})',
            'values': []
        }
        response = inventory_service.getAdUnitsByStatement(statement)
        names = []
        if 'results' in response:
            for ad_unit in response['results']:
                names.append(ad_unit['name'])
        return names

    def fetch_placement_names(ids):
        if not ids:
            return []
        id_list = ', '.join(str(i) for i in ids)
        statement = {
            'query': f'WHERE id IN ({id_list})',
            'values': []
        }
        response = placement_service.getPlacementsByStatement(statement)
        names = []
        if 'results' in response:
            for placement in response['results']:
                names.append(placement['name'])
        return names
  
    return {
        'targetedAdUnits': fetch_ad_unit_names(targetedAdUnits),
        'excludedAdUnits': fetch_ad_unit_names(excludedAdUnits),
        'targetedPlacements': fetch_placement_names(targetedPlacementIds)
    }

def get_key_name(client,key_id):
    """
    Retrieves the name of a custom targeting key from Google Ad Manager
    using the provided key ID.

    Args:
        key_id (int): The custom targeting key ID (e.g., representing "Interest", "Location", etc.).

    Returns:
        str: The name of the custom targeting key if found.
             If not found, returns a fallback string in the format 'Unknown_Key_<key_id>'.

    Example:
        >>> get_key_name(14348657)
        'User_Interest'
    """
    custom_targeting_service = client.GetService('CustomTargetingService', version='v202411')
    stmt = (ad_manager.StatementBuilder()
            .Where('id = :id')
            .WithBindVariable('id', key_id)
            .Limit(1))
    
    response = custom_targeting_service.getCustomTargetingKeysByStatement(stmt.ToStatement())
    
    if 'results' in response and len(response['results']) > 0:
        return response['results'][0]['name']
    return f"Unknown_Key_{key_id}"

def get_value_names(client , key_id, value_ids):
    """
    Fetches the names of custom targeting values from Google Ad Manager 
    for a given custom targeting key ID and a list of value IDs.

    Args:
        key_id (int): The custom targeting key ID (e.g., for "Interest", "Location", etc.).
        value_ids (List[int]): A list of custom targeting value IDs under the given key.

    Returns:
        List[str]: A list of custom targeting value names corresponding to the input IDs.
                   If a value ID is not found, 'Unknown_Value_<id>' is returned in its place.

    Example:
        >>> get_value_names(14348657, [449054745733, 449054745883])
        ['o2c', '66c']
    """
    custom_targeting_service = client.GetService('CustomTargetingService', version='v202411')
    value_id_str = ', '.join(map(str, value_ids))
    
    stmt = (ad_manager.StatementBuilder()
            .Where(f'customTargetingKeyId = :key_id AND id IN ({value_id_str})')
            .WithBindVariable('key_id', key_id)
            .Limit(500))

    response = custom_targeting_service.getCustomTargetingValuesByStatement(stmt.ToStatement())

    value_id_to_name = {}

    if 'results' in response:
        for item in response['results']:
            value_id_to_name[getattr(item, 'id')] = getattr(item, 'name')
    return [value_id_to_name.get(v_id, f"Unknown_Value_{v_id}") for v_id in value_ids]

#---------------------------------------------------------------------------------------------------------------------------------------------
#                                    Fetch Line Item Details by Name
#---------------------------------------------------------------------------------------------------------------------------------------------
#client = ad_manager.AdManagerClient.LoadFromStorage(NEW_GAM)
def get_line_items_details_by_name(client, line_item_name: str) -> List[Dict[str, Any]]:
    """
    Fetch line items from Google Ad Manager matching a given line item name substring.

    Args:
        client (AdManagerClient): An authenticated AdManager client.
        line_item_name (str): Partial or full line item name to search.

    Returns:
        List[Dict]: A list of matching line item details.
    """
    if not line_item_name or not isinstance(line_item_name, str):
        #logger.warning("Invalid line_item_name provided.")
        return []

    try:
        line_item_service = client.GetService('LineItemService', version='v202411')
        statement = ad_manager.StatementBuilder(version='v202411').Where(f"name LIKE '%{line_item_name}%'")
        response = line_item_service.getLineItemsByStatement(statement.ToStatement())
    except Exception as e:
        #logger.exception(f"Failed to fetch line items from GAM: {e}")
        return []

    results = getattr(response, 'results', [])

    if not results:
        #logger.info(f"No matching line items found for: {line_item_name}")
        return []

    all_line_item_details = []

    for item in results:
        name = getattr(item, 'name', '')
        if line_item_name not in name:
            continue

        status = getattr(item, 'status', None)

        geo = []
        excluded_geo = []
        costperunit = getattr(item , "costPerUnit", None)
        
        if costperunit:
            daily_rate = getattr(costperunit, "microAmount", None)
            daily_rate_amt = daily_rate / 1_000_000 if daily_rate else 0
        targeting = getattr(item, 'targeting', None)
        if targeting:
            geo_targeting = getattr(targeting, 'geoTargeting', None)
            if geo_targeting:
                targeted_locations = getattr(geo_targeting, 'targetedLocations', [])
                excluded_locations = getattr(geo_targeting,"excludedLocations", None)
                geo = [getattr(loc, 'displayName', 'Unknown') for loc in targeted_locations or []]
                excluded_geo = [getattr(loc, 'displayName', 'Unknown') for loc in excluded_locations or []]

        creative_sizes = []
        creatives = getattr(item, "creativePlaceholders", None)
        if creatives:
            for creative in creatives:
                targeting_name = getattr(creative, "targetingName", None)
                if targeting_name:
                    creative_sizes.append(targeting_name)

        goal = getattr(item,"primaryGoal", None)
        if goal:
            line_goal = getattr(goal,"units", None)
            
        budget_info = getattr(item, 'budget', None)

        priority = getattr(item,"priority",None)
        line_budget = None
        currency_code = None
        if budget_info:
            currency_code = getattr(budget_info, 'currencyCode', None)
            micro_amount = getattr(budget_info, 'microAmount', 0)
            line_budget = micro_amount / 1_000_000 if micro_amount else 0

        # Dates
        start_date = parse_gam_date(getattr(item, 'startDateTime', None))
        end_date = parse_gam_date(getattr(item, 'endDateTime', None))
        line_start_time = parse_gam_time(getattr(item, 'startDateTime', None))
        end_start_time = parse_gam_time(getattr(item, 'endDateTime', None))
        
        
        inventory_targeting = getattr(targeting, "inventoryTargeting", None)
        targeted_ad_unit_ids = []
        excluded_ad_unit_ids = []
        targeted_placement_ids = []
        
        if inventory_targeting:
            # Extract targetedAdUnits
            targeted_ad_units = getattr(inventory_targeting, "targetedAdUnits", [])
            if targeted_ad_units:
                targeted_ad_unit_ids = [
                    getattr(ad_unit, "adUnitId") for ad_unit in targeted_ad_units if hasattr(ad_unit, "adUnitId")
                ]

            # Extract excludedAdUnits
            excluded_ad_units = getattr(inventory_targeting, "excludedAdUnits", [])
            if excluded_ad_units:
                excluded_ad_unit_ids = [
                    getattr(ad_unit, "adUnitId") for ad_unit in excluded_ad_units if hasattr(ad_unit, "adUnitId")
                ]

            # Extract targetedPlacementIds (it's a list of strings)
            targeted_placement_ids = getattr(inventory_targeting, "targetedPlacementIds")
            
        names = get_placement_and_adunit_names_by_id(
            client, 
            targetedAdUnits=targeted_ad_unit_ids, 
            excludedAdUnits=excluded_ad_unit_ids, 
            targetedPlacementIds=targeted_placement_ids
        )
        # Safely extract names from the returned dict
        targeted_ad_units_name = names.get('targetedAdUnits', [])
        excluded_ad_units_name = names.get('excludedAdUnits', [])
        targeted_placement_names = names.get('targetedPlacements', [])
        fcap = None
        frequencyCaps = getattr(item, "frequencyCaps", None)
        if frequencyCaps:
            for caps in frequencyCaps:
                fcap = getattr(caps,"maxImpressions", None)

        audience_data = []
        customTargeting = getattr(targeting,"customTargeting",None)
        children = getattr(customTargeting, "children",None)
        if children:
            for child in children:
                child_nodes = getattr(child, "children", None)
                if child_nodes:
                    #logger.info("audience nodes exists")
                    for nodes in child_nodes:
                        key_id = getattr(nodes, "keyId", None)
                        value_id = getattr(nodes,"valueIds", None)
                        operator = getattr(nodes, "operator", None)
                        audience_data.append(
                            {
                                "key_id":key_id,
                                "value_id":value_id,
                                "operator":operator,
                            }
                        )

        transformed_audience = []
        if audience_data:
            for audience in audience_data:
                key_name = get_key_name(client , audience['key_id'])
                value_names = get_value_names(client, audience['key_id'], audience['value_id'])

                transformed_audience.append({
                    'key_name': key_name,
                    'value_names': value_names,
                    'operator': audience['operator']
                })

        daypart_run_dates = []

        daypart_targeting = getattr(targeting, 'dayPartTargeting', None)
        parsed_day_parts = []
     
        if daypart_targeting:
            day_parts_raw = getattr(daypart_targeting, 'dayParts', [])
            
            for dp in day_parts_raw:
                day_of_week = getattr(dp, 'dayOfWeek', None)
                start_time = getattr(dp, 'startTime', {})
                end_time = getattr(dp, 'endTime', {})

                parsed_day_parts.append({
                    'dayOfWeek': day_of_week,
                    'startTime': {
                        'hour': getattr(start_time, 'hour', 0),
                        'minute': getattr(start_time, 'minute', 'ZERO')
                    },
                    'endTime': {
                        'hour': getattr(end_time, 'hour', 0),
                        'minute': getattr(end_time, 'minute', 'ZERO')
                    }
                })
      
        if parsed_day_parts:
            daypart_run_dates = expand_daypart_to_dates(start_date, end_date, parsed_day_parts)
        
        all_line_item_details.append({
            "name": name,
            "status": status,
            "geo": geo if geo else [],
            "excluded_geo":excluded_geo if excluded_geo else [],
            "currency_code": currency_code,
            "total_amt": line_budget,
            "fcap":fcap,
            "start_date": start_date,
            "end_date": end_date,
            "goal":line_goal,
            "creative_size":creative_sizes if creative_sizes else [],
            "priority":priority,    
            "targetedAdUnits": targeted_ad_units_name if targeted_ad_units_name else [],
            "excludedAdUnits": excluded_ad_units_name if excluded_ad_units_name else [],
            "targetedPlacement": targeted_placement_names if targeted_placement_names else [],
            "audience": transformed_audience if transformed_audience else [],
            "day_parting_dates":daypart_run_dates if daypart_run_dates else [{"date":"Runs on single day" }],
            "cpd_daily_rate" : daily_rate_amt,
            "start_time": line_start_time if line_start_time else "00:00:00",
            "end_time": end_start_time
        })
    
    return all_line_item_details
client=ad_manager.AdManagerClient.LoadFromStorage(NEW_GAM)
#get_line_items_details_by_name(client=ad_manager.AdManagerClient.LoadFromStorage(NEW_GAM), line_item_name="28635260DOMERAYMONTILBOTH1ATFCPDTOIGEORBFULLFY25PAGEPUSHDOWNPKG219849_ppdWAP_LI_ACE")
