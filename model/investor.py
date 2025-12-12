from datetime import datetime, date

import pandas as pd
from model.investment import Investment
from model.investment_file import InvestmentFileManager

class Investor:
    def __init__(self, user, investor_name):
        self.user = user
        self.name = investor_name
        investor_file = InvestmentFileManager(user.user_id, investor_name)
        self.investments = []
        for investment_rec in investor_file.investments:
            buy_txns_count = sum(1 for txn in investment_rec.Transactions if txn.type == "buy")
            if buy_txns_count > 0:
                self.investments.append(Investment(self, investment_rec))

        defective_investments = [investment for investment in self.investments if investment.is_defective_data]
        for investment in defective_investments:
            print(investment.defect_desc)
        self.investments = [investment for investment in self.investments if not investment.is_defective_data]

    def get_filtered_investments(self, tax_treatments=None, mf_categories=None, hide_zero_balance_before=None,
                                 sold_in_fy=None, ):
        filtered_investments = []
        for investment in self.investments:
            c1 = (not tax_treatments   or
                  (investment.tax_treatment is not None and investment.tax_treatment in tax_treatments))
            c2 = (not mf_categories    or
                  investment.mf_category is not None and investment.mf_category   in mf_categories)
            c3 = not hide_zero_balance_before or (investment.last_txn.txn_date >= hide_zero_balance_before or investment.holding > 0)
            c4 = not sold_in_fy or any([txn for txn in investment.sell_txns if txn.fy==sold_in_fy])
            if c1 and c2 and c3 and c4:
                filtered_investments.append(investment)
        return filtered_investments

    @property
    def tags(self):
        list_of_tags = [investment.tags for investment in self.investments]
        unique_tags = list({tag for tags in list_of_tags for tag in tags})
        return unique_tags

    @property
    def compiled_tags(self):
        # Combine compiled tags dictionaries from all investments
        combined = {}
        for investment in self.investments:
            for cat, subs in investment.compiled_tags.items():
                combined.setdefault(cat, set())  # Ensure the category exists (always)
                if subs:     # Add subcategories if any
                    combined[cat].update(subs)

        combined = {cat: sorted(list(subs)) for cat, subs in combined.items()}
        return combined

    def __iter__(self):
        return iter(self.investments)
# End of Investor Class

