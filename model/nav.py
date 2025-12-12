import requests
import re
import pandas as pd
import time

# from model.user import User
import utils.utils as utils


class NAV:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # self.nav_df = pd.DataFrame([], columns=['isin', 'nav', 'nav_date'])
        self.nav_pattern = re.compile(r'^([0-9]{6});(.*?);.*?;.*?;([0-9.]+);([0-9]{2}-[a-zA-Z]{3}-(20[2-4][0-9]))$')

        self.nav_url = r'https://www.amfiindia.com/spages/NAVOpen.txt'
        self.nav_csv_file = r'data\common\nav.csv'
        self.nav_df = pd.DataFrame()
        self.load()

    def download_from_amfi(self):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(self.nav_url, headers=headers, timeout=20)
        if response.status_code != 200:
            # response.raise_for_status()
            ts = int(time.time())
            response = requests.get(f"{self.nav_url}?t={ts}", headers=headers, timeout=20)
            # response = requests.get(self.nav_url)
            if response.status_code != 200:
                # raise Exception(f"Failed to fetch NAVAll.txt, status {response.status_code}")
                print("Not able to download NAV.")
                self.nav_df = pd.DataFrame()    # empty

        if response.status_code == 200:
            self.nav_df = parse_nav_text(response.text, self.nav_pattern)
        return self

    def load(self):
        # Uncomment
        self.download_from_amfi()
        if not self.nav_df.empty:  # Download successful - save csv for future possible use
            print(f'Downloaded NAVs from {self.nav_url}')
            self.nav_df.to_csv(self.nav_csv_file, index=False)

        if self.nav_df.empty:  # If Download unsuccessful...
            print (f'Reading previous values from saved csv file.')
            try:    # Read previously saved NAV csv file
                self.nav_df = pd.read_csv(self.nav_csv_file)
            except Exception as e:
                raise FileNotFoundError(f'{self.nav_csv_file} not found for reading.')

        # We have isin, nav and nav_date in the DF with isin as index
        self.nav_df["nav_date"] = self.nav_df["nav_date"].apply(utils.normalize_date)
        self.nav_df.set_index('isin', inplace=True)
        return self


def parse_nav_text(nav_file_text, pattern):
    lines = nav_file_text.splitlines()
    nav_rows = []
    for line in lines:
        match = pattern.match(line)
        if match:
            amfi_code, isin, nav, nav_date, nav_year = match.groups()
            # nav_date = datetime.strptime(nav_date, '%d-%b-%Y').date()
            # nav_date = utils.normalize_date(nav_date)
            if int(nav_year) >= 2024:
                nav_rows.append({
                    'isin': isin,
                    'nav': float(nav),
                    'nav_date': nav_date,
                })
    nav_df = pd.DataFrame(nav_rows)
    return nav_df



nav_object = NAV()

def nav_and_date(isin):
    # print(nav_object.nav_df.head())
    # print(nav_object.nav_df.tail())
    # print (nav_object.nav_df["nav"].get(isin, None), nav_object.nav_df["nav_date"].get(isin, None))
    # # return nav_object.nav_df["nav"].get(isin, None), nav_object.nav_df["nav_date"].get(isin, None)
    # print(isin, nav_object.nav_df.index)
    return (nav_object.nav_df.loc[isin, 'nav'],
            nav_object.nav_df.loc[isin, 'nav_date'],
            ) if isin in nav_object.nav_df.index else (None, None)

def nav(isin):
    return nav_object.nav_df.loc[isin, 'nav'] if isin in nav_object.nav_df.index else None
def nav_date(isin):
    return nav_object.nav_df.loc[isin, 'nav_date'] if isin in nav_object.nav_df.index else None

def nav_download():
    nav_object.load()

def nav_on_31012018(isin):
    return {
        "INF769K01BI1": 54.687,  # Mirae Asset Large and Midcap Fund - Dir Growth
        "INF769K01AX2": 51.799,  # Mirae Asset Large Cap Fund - Dir Growth
        "INF760K01EI4": 101.1400,  # Canara Robeco Large and Mid Cap Fund - Dir Growth
        "INF109K015K4": 277.8452,  # ICICI Prudential Multi-Asset Fund - Dir Growth
        "INF109K016E5": 21.8368,  # ICICI Prudential All Seasons Bond Fund - Dir Growth
    }.get(isin, 0)


def download_mfapi(isin_set):

    for isin in isin_set:
        print(f"{isin}")


if __name__ == '__main__':
    print(nav_and_date('INF209KA12Z1'))
    print(nav_and_date('INF209K01LR8'))
    print(nav_and_date('INF209K01LV0'))