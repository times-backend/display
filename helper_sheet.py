from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import pandas as pd
import numpy as np
import gspread
import os
import re

load_dotenv()
G_CREDS = os.getenv("G_CREDS")
sheet_url = os.getenv("sheet_url")

def get_gspread_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(G_CREDS, scope)
    return gspread.authorize(creds)

def placements(worksheet_name, sheet_url):
    client = get_gspread_client()
    worksheet = client.open_by_url(sheet_url).worksheet(worksheet_name)
    data = worksheet.get_all_values()
    df = pd.DataFrame(data[1:], columns=data[0])
    return df

def filter_df(TAB,sheet_url):
    # Load data
    for_filter_df = placements(
        TAB,
        sheet_url
    )

    # ---------------------------------------------------
    # 1. CLEANUP TEXT
    # ---------------------------------------------------

    # Remove word "website" (case-insensitive)
    for_filter_df = for_filter_df.applymap(
        lambda x: re.sub(r'website', '', str(x), flags=re.IGNORECASE)
    )

    # Remove prefix 'TIL_' from Ad Unit Type
    for_filter_df['Ad Unit Type'] = (
        for_filter_df['Ad Unit Type']
        .str.replace(r'^TIL_', '', regex=True)
    )

    # Normalize MREC PPD to MREC
    for_filter_df = for_filter_df.replace(
        {r'(?i)\bMREC PPD\b': 'MREC'}, regex=True
    )
    for_filter_df = for_filter_df.replace(
        {r'(?i)\bMWEB PPD\b': 'TOP_BANNER'}, regex=True
    )
    for_filter_df = for_filter_df.replace(
        {r'(?i)\bBillboard\b': 'Leaderboard'}, regex=True
    )
    # ---------------------------------------------------
    # 2. PLATFORM NORMALIZATION (clean Website column)
    # ---------------------------------------------------

    platform_map = {
        r'(?i)\b(Mobile Site?|MWEB|Mobile)\b': 'MWEB',
        r'(?i)\b(Android Apps?|Android APP|Android)\b': 'AOS',
        r'(?i)\b(iOS Apps?|iOS App)\b': 'IOS',
        r'(?i)\b(Amp site?|Amp sites?)\b': 'AMP'
    }

    for pattern, replacement in platform_map.items():
        for_filter_df['Website'] = for_filter_df['Website'].str.replace(
            pattern, replacement, regex=True
        )

    # ---------------------------------------------------
    # 3. PLATFORM DETECTION (final platform column)
    # ---------------------------------------------------

    for_filter_df["platform"] = (
        for_filter_df["Website"]
        .str.extract(r'\b(AMP|MWEB|AOS|IOS)\b', expand=False)
        .fillna("Web")
    )
    # Remove platform codes from Website column
    for_filter_df['Website'] = (
        for_filter_df['Website']
        .str.replace(r'\b(AMP|MWEB|AOS|IOS)\b', '', regex=True, case=False)
        .str.replace(r'\s+', ' ', regex=True)
    )

    return for_filter_df


