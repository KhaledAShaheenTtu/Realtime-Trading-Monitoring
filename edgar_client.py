"""
EDGAR client utilities for fetching SEC filings metadata and writing CSV files.

This module provides:
- search_company_filings_by_cik_or_name(name_or_cik): uses SEC EDGAR search API to find company filings
- fetch_filings_for_keywords(keywords, limit): uses EDGAR full-text search for keywords
- write_filings_to_csv(filings, output_path): writes list of filings dicts to CSV

Notes:
- No API key is required for EDGAR public endpoints.
- To avoid heavy scraping, this implementation uses the public "https://data.sec.gov/submissions/CIK{cik}.json" when CIK known
  or the full-text search API at "https://efts.sec.gov/LATEST/search-index" for keyword searches.
- Adds a simple user-agent header as required by SEC policy.
"""

import requests
import datetime
import csv
import os
import time
from typing import List, Dict, Optional

# SEC requires a descriptive User-Agent identifying the requester. Adjust email if you want.
USER_AGENT = "Realtime-Trading-Monitoring/1.0 (mailto:example@example.com)"
HEADERS = {"User-Agent": USER_AGENT, "Accept": "application/json"}

# Basic rate limit pause between requests to be polite
RATE_LIMIT_SECONDS = 0.2


def _ensure_output_path(output_path: str):
    dirpath = os.path.dirname(output_path)
    if dirpath and not os.path.exists(dirpath):
        os.makedirs(dirpath, exist_ok=True)


def _to_utc_iso_from_date(date_str: Optional[str]) -> Optional[str]:
    """Convert a YYYY-MM-DD string into an ISO UTC timestamp (T00:00:00Z).

    Returns None if input is falsy or invalid.
    """
    if not date_str:
        return None
    try:
        # Parse naive date
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        # Assume midnight UTC
        return dt.replace(tzinfo=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None


def fetch_submissions_by_cik(cik: str) -> Optional[Dict]:
    """Fetch the submissions JSON for a CIK (zero-padded to 10 digits).

    Returns the parsed JSON or None on error.
    """
    padded = str(cik).zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{padded}.json"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        time.sleep(RATE_LIMIT_SECONDS)
        if resp.status_code == 200:
            return resp.json()
        else:
            return None
    except Exception:
        return None


def search_filings_full_text(query: str, limit: int = 10) -> List[Dict]:
    """Search EDGAR full text search endpoint for filings containing the query.

    Uses GET with 'q' parameter to avoid 403 errors seen with POST in some environments.

    Returns list of filings metadata dicts. Keeps the results compact.
    """
    url = "https://efts.sec.gov/LATEST/search-index"
    params = {
        "q": query,
        "from": 0,
        "size": max(1, int(limit))
    }
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        time.sleep(RATE_LIMIT_SECONDS)
        if resp.status_code == 200:
            j = resp.json()
            hits = j.get('hits', {}).get('hits', [])
            results = []
            for h in hits:
                source = h.get('_source', {})
                # Current GET schema fields (observed):
                # 'form' (form type), 'file_date', 'adsh' (accession), 'ciks' (list), 'display_names' (list)
                ciks = source.get('ciks') or []
                display_names = source.get('display_names') or []
                cik_val = None
                if isinstance(ciks, list) and ciks:
                    cik_val = ciks[0]
                company_name = None
                if isinstance(display_names, list) and display_names:
                    company_name = display_names[0]
                acc = source.get('adsh')
                detail_url = None
                if cik_val and acc:
                    try:
                        cik_int = int(str(cik_val))
                        acc_nodash = acc.replace('-', '')
                        # Link to filing index page
                        detail_url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/{acc}-index.htm"
                    except Exception:
                        detail_url = None
                results.append({
                    'accessionNumber': acc,
                    'cik': cik_val,
                    'companyName': company_name,
                    'form': source.get('form'),
                    'filedDate': _to_utc_iso_from_date(source.get('file_date')),
                    'detail_url': detail_url
                })
            return results
        else:
            return []
    except Exception:
        return []


def extract_filings_from_submissions(submissions_json: Dict, max_filings: int = 20) -> List[Dict]:
    """Given the company submissions JSON, extract recent filings as a list of dicts."""
    filings = []
    if not submissions_json:
        return filings
    # The 'filings' -> 'recent' section contains arrays aligned by index
    recent = submissions_json.get('filings', {}).get('recent', {})
    keys = ['accessionNumber', 'reportDate', 'filingDate', 'form', 'primaryDocument', 'primaryDocDescription']
    rows = []
    if recent:
        count = min(max_filings, len(recent.get('accessionNumber', [])))
        for i in range(count):
            row = {
                'accessionNumber': recent.get('accessionNumber', [None]*count)[i],
                'cik': submissions_json.get('cik'),
                'companyName': submissions_json.get('name'),
                'form': recent.get('form', [None]*count)[i],
                'filedDate': _to_utc_iso_from_date(recent.get('filingDate', [None]*count)[i]),
                'reportDate': recent.get('reportDate', [None]*count)[i],
                'primaryDocument': recent.get('primaryDocument', [None]*count)[i],
                'primaryDocDescription': recent.get('primaryDocDescription', [None]*count)[i],
            }
            # Derive a direct filing detail url
            cik_val = submissions_json.get('cik')
            acc_no = row['accessionNumber']
            if acc_no and cik_val:
                try:
                    cik_int = int(cik_val)
                except Exception:
                    cik_int = None
                acc_no_nodash = acc_no.replace('-', '')
                if cik_int is not None:
                    # Use stable index page and direct primary doc link (avoid Inline XBRL viewer dependency)
                    row['primaryDocumentUrl'] = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_no_nodash}/{row.get('primaryDocument','')}" if row.get('primaryDocument') else None
                    row['detail_url'] = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_no_nodash}/{acc_no}-index.htm"
                else:
                    row['detail_url'] = None
            else:
                row['detail_url'] = None
            rows.append(row)
        filings = rows
    return filings


def write_filings_to_csv(filings: List[Dict], output_path: str):
    """Write filings list of dicts to CSV with a header.
    """
    if not filings:
        return
    _ensure_output_path(output_path)
    default_headers = ['companyName', 'cik', 'form', 'filedDate', 'reportDate', 'accessionNumber', 'primaryDocument', 'primaryDocDescription', 'primaryDocumentUrl', 'detail_url']
    headers = list({k for f in filings for k in f.keys()})
    # Ensure deterministic header order
    ordered = [p for p in default_headers if p in headers] + sorted([h for h in headers if h not in default_headers])
    with open(output_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(ordered)
        for fil in filings:
            row = [fil.get(h, '') for h in ordered]
            writer.writerow(row)


# High-level convenience functions

def get_and_write_filings_for_keyword(keyword: str, instrument: str, output_dir: str = 'data', limit: int = 20) -> str:
    """Search for filings matching `keyword` (full-text) and write CSV into `output_dir/sec_filings_{instrument}.csv`.

    Returns the output file path.
    """
    filings = search_filings_full_text(keyword, limit=limit)
    if not filings:
        return None
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{output_dir}/sec_filings_{instrument}.csv")
    write_filings_to_csv(filings, output_path)
    return output_path


def get_and_write_filings_for_cik(cik: str, instrument: str, output_dir: str = 'data', limit: int = 50) -> str:
    """Fetch company submissions by CIK and write recent filings to CSV."""
    submissions = fetch_submissions_by_cik(cik)
    filings = extract_filings_from_submissions(submissions, max_filings=limit)
    if not filings:
        return None
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{output_dir}/sec_filings_{instrument}.csv")
    write_filings_to_csv(filings, output_path)
    return output_path


def get_and_write_filings_for_ciks(ciks: List[str], instrument: str, output_dir: str = 'data', limit_each: int = 20) -> Optional[str]:
    """Fetch submissions for multiple CIKs, aggregate recent filings, and write a combined CSV.

    Returns output file path, or None if no filings found.
    """
    all_filings: List[Dict] = []
    for cik in ciks:
        submissions = fetch_submissions_by_cik(cik)
        filings = extract_filings_from_submissions(submissions, max_filings=limit_each)
        if filings:
            all_filings.extend(filings)
    # Dedupe by accessionNumber
    seen = set()
    deduped = []
    for f in all_filings:
        acc = f.get('accessionNumber')
        if acc and acc not in seen:
            seen.add(acc)
            deduped.append(f)
    if not deduped:
        return None
    # Sort by filedDate desc when available
    def filed_key(x):
        return x.get('filedDate') or ''
    deduped.sort(key=filed_key, reverse=True)
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{output_dir}/sec_filings_{instrument}.csv")
    write_filings_to_csv(deduped, output_path)
    return output_path


def get_and_write_combined_btc_ton_mag7(
    output_dir: str = 'data',
    btc_limit: int = 50,
    ton_limit: int = 50,
    mag7_limit_each: int = 20,
    output_file: Optional[str] = None,
    append: bool = True,
    dedupe_existing: bool = True,
) -> Optional[str]:
    """Fetch BTC and TON via keyword search and MAG7 via CIK list, combine into one CSV with instrument column.

    - output_file: if provided, write to this path (relative paths are resolved next to this module); otherwise, use
      f"{output_dir}/sec_filings_combined.csv".
    - append: when True, append to an existing file and write header only if the file is empty; otherwise overwrite.
    - dedupe_existing: when True and appending, skip rows already present in the existing file by key (accessionNumber, instrument).

    Returns the output file path or None if no filings found across all instruments.
    """
    # BTC
    btc_filings = search_filings_full_text('bitcoin', limit=btc_limit)
    for f in btc_filings:
        f['instrument'] = 'BTC'

    # TON: revert back to simple 'ton' query (fallback from refined query)
    ton_query_primary = '"The Open Network" OR "TON Foundation" OR Toncoin'
    ton_filings = search_filings_full_text(ton_query_primary, limit=ton_limit)
    if not ton_filings:
        ton_filings = search_filings_full_text('ton', limit=ton_limit)
    for f in ton_filings:
        f['instrument'] = 'TON'

    # MAG7 via CIK aggregation
    mag7_ciks = ['0000320193','0000789019','0001652044','0001018724','0001326801','0001045810','0001318605']
    mag7_sub_filings: List[Dict] = []
    for cik in mag7_ciks:
        subs = fetch_submissions_by_cik(cik)
        sub_filings = extract_filings_from_submissions(subs, max_filings=mag7_limit_each)
        if sub_filings:
            mag7_sub_filings.extend(sub_filings)
    for f in mag7_sub_filings:
        f['instrument'] = 'MAG7'

    combined = btc_filings + ton_filings + mag7_sub_filings
    if not combined:
        return None

    # Dedupe by accessionNumber + instrument to avoid collisions across groups, then sort by filedDate desc
    seen = set()
    unique = []
    for f in combined:
        key = (f.get('accessionNumber'), f.get('instrument'))
        if key not in seen:
            seen.add(key)
            unique.append(f)

    def filed_key(x):
        # Sort by filedDate string, works with ISO format
        return x.get('filedDate') or ''
    unique.sort(key=filed_key, reverse=True)

    # Resolve output path
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if output_file:
        # Use provided path, resolve relative to module directory
        output_path = output_file if os.path.isabs(output_file) else os.path.join(base_dir, output_file)
    else:
        output_path = os.path.join(base_dir, f"{output_dir}/sec_filings_combined.csv")

    # Prepare headers
    preferred = ['instrument', 'companyName', 'cik', 'form', 'filedDate', 'accessionNumber', 'reportDate', 'primaryDocument', 'primaryDocDescription', 'primaryDocumentUrl', 'detail_url']
    headers = list({k for f in unique for k in f.keys()})
    ordered = [p for p in preferred if p in headers] + sorted([h for h in headers if h not in preferred])

    _ensure_output_path(output_path)

    file_exists = os.path.exists(output_path) and os.path.getsize(output_path) > 0

    # If appending and file exists, preserve existing header order and dedupe
    existing_header = None
    existing_keys = set()
    if append and file_exists:
        try:
            with open(output_path, 'r', newline='', encoding='utf-8') as rf:
                reader = csv.reader(rf)
                existing_header = next(reader, None)
                if existing_header:
                    # Build index map
                    try:
                        acc_idx = existing_header.index('accessionNumber')
                    except ValueError:
                        acc_idx = None
                    try:
                        inst_idx = existing_header.index('instrument')
                    except ValueError:
                        inst_idx = None
                    for row in reader:
                        if acc_idx is not None and inst_idx is not None and len(row) > max(acc_idx, inst_idx):
                            existing_keys.add((row[acc_idx], row[inst_idx]))
                        elif acc_idx is not None and len(row) > acc_idx:
                            existing_keys.add((row[acc_idx], None))
        except Exception:
            # If reading existing file fails, proceed without dedupe preservation
            existing_header = None
            existing_keys = set()

    write_header_now = not (append and file_exists)

    with open(output_path, 'a' if append else 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        header_to_use = existing_header if (append and file_exists and existing_header) else ordered
        if write_header_now:
            writer.writerow(header_to_use)

        # Write rows, respecting header order and dedupe if requested
        for fil in unique:
            key = (fil.get('accessionNumber'), fil.get('instrument'))
            if dedupe_existing and (append and file_exists) and (key in existing_keys):
                continue
            row = [fil.get(h, '') for h in header_to_use]
            writer.writerow(row)

    return output_path


if __name__ == '__main__':
    # quick manual smoke test (no network mocking here)
    print('Searching for Bitcoin filings...')
    p = get_and_write_filings_for_keyword('bitcoin', 'BTC', limit=10)
    print('Wrote', p)
