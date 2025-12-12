"""
MF Master Data - csv file
1. If ISIN is not already in the file, add it as new row
2. Scheme Name obtained from CAS is also added when entry for ISIN is created.
3. If ISIN already exists, return corresponding data items.
4. Updating the csv (as of now, manually)
4a. Modify scheme name if required.
4b. Add tax_treatment (for view) -> for FY 2025-26:
    Debt (always slab rate)
    Hybrid (<2Y slab rate, > 2Y LTCG 12.5%)
    Equity (<1Y STCG 20%, >1Y LTCG 12.5%)
5. Add mf_category (Primarily for view filtering):
    Debt
    Hybrid - Consvt
    Hybrid - Multi
    Equity - Small
    Equity - Multi
    Equity - Mid
    Equity - Global
6. Add exit load duration (days)
7. add LTCG Days (how many days after purchase LTCG would be applicable)
"""
import pandas as pd
import model.investor as investor


class MfStatic:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # isin is passed when we want to fetch data for this isin or create if not already exists
        # investor is passed when we want list of values for invested folios of the given investor
        self.filename = r'data\hemant\common\mf_master.csv'
        self.defaults = {'scheme_name': 'scheme_name',
                          'tax_treatment': 'Unknown',
                          'mf_category': 'Unknown',
                          'exit_load_days': 999,
                          'ltcg_days': 9999,
                          }
        self.scheme_name    = None
        self.tax_treatment  = None
        self.mf_category    = None
        self.exit_load_days = None
        self.ltcg_days      = None
        try:
            self.schemes_df = pd.read_csv(self.filename, index_col='isin')
        except FileNotFoundError:
            # Create empty df (First ever use of the application)
            print('MF Static data file not found. Creating one.')
            self.schemes_df = (pd.DataFrame(columns=list(self.defaults.keys())))

        # self.load()

        # df[df.index.isin(['INF209K01UU3', 'INF846K01K35'])]
    def load(self):
        self.scheme_name = sorted(set(self.schemes_df['scheme_name']))
        self.tax_treatment = sorted(set(self.schemes_df['tax_treatment']))
        self.mf_category = sorted(list(set(self.schemes_df['mf_category'])))
        self.exit_load_days = sorted(set(self.schemes_df['exit_load_days']))
        self.ltcg_days = sorted(set(self.schemes_df['ltcg_days']))
        # print('Tax Treatment in Mf Master= ', self.tax_treatment)
        # print('MF Category in Mf Master= ', self.mf_category)
        return self


    def for_isin(self, isin, scheme_name, create_default=True):
        if isin not in self.schemes_df.index:   # New mf scheme in the portfolio
            # ISIN value is given but it does not exist in mf_static data - create default
            self.defaults['scheme_name'] = scheme_name
            self.schemes_df.loc[isin] = self.defaults
            # self.schemes_df.loc[isin]['scheme_name'] = scheme_name
            self.schemes_df.to_csv(self.filename, index_label='isin')
            # self.schemes_df.set_index(isin, inplace=True)

        statics = self.schemes_df.loc[isin]
        self.scheme_name = statics.scheme_name
        self.tax_treatment = statics.tax_treatment
        self.mf_category = statics.mf_category
        self.exit_load_days = statics.exit_load_days
        self.ltcg_days = statics.ltcg_days
        return self

    def for_investor(self, investor):
        investor_schemes_df = self.schemes_df[self.schemes_df.index.isin(investor.isin_set)]
        self.scheme_name = sorted(set(investor_schemes_df['scheme_name']))
        self.tax_treatment = sorted(set(investor_schemes_df['tax_treatment']))
        self.mf_category = sorted(list(set(investor_schemes_df['mf_category'])))
        self.exit_load_days = sorted(set(investor_schemes_df['exit_load_days']))
        self.ltcg_days = sorted(set(investor_schemes_df['ltcg_days']))
        return self


    def get(self, isin, scheme_name):
        if isin not in self.schemes_df.index:
            self.schemes_df.loc[isin] = {'scheme_name': scheme_name,
                                      'tax_treatment': 'Unknown',
                                      'mf_category': 'Unknown',
                                      'exit_load_days': 999,
                                      'ltcg_days': 9999,
                                         }
            # self.schemes.set_index(isin, inplace=True)
            self.schemes_df.to_csv(self.filename)
        return dict(self.schemes_df.loc[isin])

static_data = MfStatic()