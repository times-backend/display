import os
import pandas as pd

def read_any(path: str):
    """Reads any Excel or CSV file and returns a pandas DataFrame."""
    ext = os.path.splitext(path)[-1].lower()
    if ext in [".xls", ".xlsx"]:
        return pd.read_excel(path, engine=None)
    elif ext == ".csv":
        return pd.read_csv(path)
    else:
        return pd.read_excel(path, engine=None)


def get_latest_file(folder: str):
    """Get the most recently modified file in the given folder."""
    files = [os.path.join(folder, f) for f in os.listdir(folder) if not f.startswith(".")]
    if not files:
        raise FileNotFoundError(f"No files found in folder: {folder}")
    return max(files, key=os.path.getmtime)


def read_file(line_item_name: str, folder: str = "downloads"):
    """
    Load the latest Excel/CSV file and return only the row(s)
    where the Line Item Name (column H) matches or contains `line_item_name`.
    Supports multiple comma-separated line items in a single cell.
    Returns a single dict if one match, else a list of dicts.
    """
    path = get_latest_file(folder)
    print(f"📄 Loading: {path}")

    df = read_any(path)
    df = df.dropna(how="all")

    # --- Handle column H as "Line Item Name" ---
    if len(df.columns) >= 8:
        col_h_name = df.columns[7]
    else:
        raise ValueError("The file does not have a column H (8th column).")

    # --- Normalize target ---
    target = line_item_name.strip().lower()

    # --- Match logic: supports comma-separated names ---
    def match_line_item(cell):
        if pd.isna(cell):
            return False
        values = [v.strip().lower() for v in str(cell).split(",") if v.strip()]
        return target in values

    filtered = df[df[col_h_name].apply(match_line_item)]

    if filtered.empty:
        print(f"⚠️ No matching row found for: {line_item_name}")
        return {}
    
    records = filtered.to_dict(orient="records")

    # Return single dict if only one match
    return records[0] if len(records) == 1 else records

