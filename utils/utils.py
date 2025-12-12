from babel.numbers import format_currency, format_decimal, format_compact_currency
from datetime import datetime, date, timedelta
import pickle
from pathlib import Path

def rupees_str(value, decimal_places=0, symbol=u'₹'):
    return format_currency(
                round(value, decimal_places), # if decimal_places else round(value),
                'INR',
                locale='en_IN',
                currency_digits=False if not decimal_places else True,
                format=symbol+u'#,##,##0') if value else '--' #symbol+'0'

def number_str(value, decimal_places=0, suffix="", compact="", zero_str="—"): # --
    if not isinstance(value, (float, int)):
        return value    # Ignore if it is not float or int

    value = round(value,4)
    if value == 0:
        return zero_str
    if compact:
        value /= 1_00_00_000 if compact == 'C' else 1_00_000 if compact == 'L' else 1_000 if compact == 'K' else 1

    f = '#,##,##0' if not decimal_places else '#,##,##0.' + ('0' * decimal_places)
    formatted_str = format_decimal(value, locale='en_IN', format=f,) if value != 0 else zero_str
    # formatted_str += "*" if suffix else ""
    return formatted_str + suffix + (compact if value != 0 else "")

def current_fy():
    return get_fy(date.today())

def previous_fy(n=-1):
    return get_fy(date.today() + timedelta(days=365*n))

def get_fy(a_date = date.today()):
    year = a_date.year
    month = a_date.month
    return f'{year}-{year + 1 - 2000:02d}' if month >= 4 else f'{year - 1}-{year - 2000:02d}'

def get_last_n_fy(start_date = date.today(), n=3):
    # fy_list = []
    # for i in range(n):
    #     fy_list.append(get_fy(start_date - timedelta(days=i*365)))
    # return fy_list
    return [get_fy(start_date - timedelta(days=i*365)) for i in range(n)]

def get_timeframe(fy=None, cy=None, mo=None):
    # Compute from and to dates for the given Fin Year or Cal Year or Cal Month
    from_date, to_date = None, None
    fy = str2fy(fy) if isinstance(fy, str) else fy # This will convert FY to 4 digit number
    cy = int(cy) if isinstance(cy, str) else cy
    mo = int(mo) if isinstance(mo, str) else mo
    if mo is not None:  # Timeframe of a given month
        if fy is not None:  # Given month of a Financial Year (convert to calendar year)
            # Financial year month 1 is month 4 of calendar year (April is 1, March is 12) - This will allow is to
            # run a loop on Fin Year months from Apr to Mar ( 1 to 12)
            # Apr-2025 to Dec-2025 => FY is 2026 and CY = 2025
            # Jan-2025 to Mar-2025 => FY is 2025 and CY is 2025
            cy = fy-1 if mo <= 9 else fy
            mo += 3 if mo <= 9 else (-9) # Now April is 4 and March is 12
        # Time frame of a given month of a Calendar Year
        from_date = date(cy, mo, 1)
        to_date = date(cy if mo < 12 else cy+1, (mo+1) if mo < 12 else 1, 1)-timedelta(days=1)
    elif cy is not None:
        from_date = date(cy, 1, 1)  #
        to_date = date(cy, 12, 31)
    elif fy is not None:
        from_date = date(fy-1, 4, 1)    # 01-04-(FY-1)
        to_date = date(fy, 3, 31)       # 31-03-fyfy

    return from_date, to_date


def current_fy_start_date():
    return get_timeframe(fy=current_fy())[0]

def current_fy_end_date():
    return get_timeframe(fy=current_fy())[1]

def previous_fy_start_date(n=-1):
    return get_timeframe(fy=previous_fy(n))[0]

def previous_fy_end_date(n=-1):
    return get_timeframe(fy=previous_fy(n))[1]

def fy_qtr_start_date(fy, qtr):
    # example fy="2024-25", qtr=2 ==> 16-06-2024
    if not isinstance(fy, str) or (1 > qtr > 5):
        raise TypeError('fy_qtr_start_date: fy must be str and qtr within 1:5')
    qtr_index = qtr - 1
    dates = ["1-Apr", "16-Jun", "16-Sep", "16-Dec", "16-Mar"]
    fy = fy[:4] if qtr < 5 else str(int(fy[:4])+1)
    start_date = datetime.strptime(f"{dates[qtr_index]}-{fy}", "%d-%b-%Y").date()
    return start_date

def fy_qtr_end_date(fy, qtr):
    # example fy="2024-25", qtr=2 ==> 15-09-2024
    if not isinstance(fy, str) or (1 > qtr > 5):
        raise TypeError('fy_qtr_start_date: fy must be str and qtr within 1:5')
    qtr_index = qtr - 1
    dates = ["15-Jun", "15-Sep", "15-Dec", "15-Mar", "31-Mar"]
    fy = fy[:4] if qtr < 4 else str(int(fy[:4])+1)
    end_date = datetime.strptime(f"{dates[qtr_index]}-{fy}", "%d-%b-%Y").date()
    return end_date


def fy2str(fy):
    return f'{fy-1:4d}-{fy-2000:2d}'

def str2fy(fy):
    # examples: "2025" ==> 2025, "2025-26" ==> 2026
    if isinstance(fy, str):
        fy = int(fy) if len(fy) == 4 else (int(fy[:4]) + 1) if len(fy) == 7 else None
    return fy

def normalize_date(date_str):
    for fmt in ("%d-%b-%y", "%d-%b-%Y", "%Y-%m-%d", "%d-%m-%Y", "%d-%m-%y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unknown date format: {date_str}")

def is_date_in_fy(date_obj, fy_str):
    # Example fy_str: "2025-24"
    start_year = int(fy_str.split('-')[0])
    start_date = date(start_year, 4, 1)
    end_date = date(start_year + 1, 3, 31)
    return start_date <= date_obj <= end_date

def compute_month_end_dates(from_date=date.today(), how_many=2,):
    month_end_dates = []
    count = 0
    month_end_date = from_date
    while True:
        month_end_date = month_end_date + timedelta(days=1)
        year = month_end_date.year
        month = month_end_date.month + 1
        if month > 12:
            month = 1
            year += 1
        month_end_date = date(year, month, 1) - timedelta(days=1)
        if count < how_many:
            month_end_dates.append(month_end_date)
            count += 1
        else:
            break
    return month_end_dates

# def compute_month_end_dates(from_date=date.today(), how_many=2, stop_before=current_fy_end_date()):
#     month_end_dates = []
#     count = 0
#     month_end_date = from_date
#     while True:
#         month_end_date = month_end_date + timedelta(days=1)
#         year = month_end_date.year
#         month = month_end_date.month + 1
#         if month > 12:
#             month = 1
#             year += 1
#         month_end_date = date(year, month, 1) - timedelta(days=1)
#         if count < how_many and month_end_date < stop_before:
#             month_end_dates.append(month_end_date)
#             count += 1
#         else:
#             break
#     return month_end_dates


def compile_tags(tags: list[str]) -> dict[str, list[str]]:
    # Tags input are lists of strings in format <category:str> or <category:str>/<sub-category:str>.
    # These are converted to dict {<category:str>: [<category:str>, ...], ...} format (i.e. from list of strings to dictionary)
    result = {}
    for tag in tags:
        tag = tag.strip()
        if not tag:
            continue  # skip empty strings

        if "/" in tag:
            category, subcategory = map(str.strip, tag.split("/", 1))
            if not category or not subcategory:
                continue  # skip malformed tags
            result.setdefault(category, set()).add(subcategory)
        else:
            # standalone category, ensure it exists in dict
            result.setdefault(tag, set())

    # convert sets to sorted lists for consistency (optional)
    return {cat: sorted(list(subs)) for cat, subs in result.items()}

