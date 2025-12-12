from datetime import timedelta, date, datetime

from model.xirr import xirr, cagr
import model.nav as nav
import utils.utils as utils

class Investment:
    # def __init__(self, investor, isin, folio, scheme_name, transactions):
    def __init__(self, investor, investment_data_class):
        # investment_rec = asdict(investment_data_class)
        investment_rec = investment_data_class
        self.investor = investor
        self.is_defective_data = False
        self.defect_desc = ''

        self.isin = investment_rec.ISIN
        self.folio = investment_rec.Folio
        self.scheme_name = investment_rec.SchemeName

        # transactions = sorted(investment_rec.Transactions, key=lambda txn: txn.date)
        self.holding = round(sum([txn.quantity for txn in investment_rec.Transactions]), 4)

        self.buy_txns  = [BuyTxn(self, txn_rec) for txn_rec in investment_rec.Transactions if txn_rec.type == "buy"]
        self.sell_txns = [SellTxn(self, txn_rec) for txn_rec in investment_rec.Transactions if txn_rec.type == "sell"]

        self.txns = sorted(self.buy_txns + self.sell_txns, key=lambda txn: txn.txn_date,)
        # if len(self.buy_txns) > 0:
        self.last_txn = self.txns[-1]

        # Compute cumulative balance
        self._compute_txns_cumulative_balance()
        # self.matched_txns = []  # Split txns after matching sold units with bought units
        self.matched_txns = self._match_txns()

        # Check data validity....
        unsold_units = round(sum(txn.unsold_units for txn in self.buy_txns))
        if unsold_units != round(self.holding):
            self.is_defective_data = True
            self.defect_desc = (f'Unmatched holding found for {self.scheme_name} ({self.isin}, '
                                f'{self.folio}) of {investor.name}\n '
                                f'Holding = {round(self.holding)}, Unsold units = {unsold_units}'
                                )

        # Fetch current NAV
        self.nav = nav.nav(self.isin) or self.txns[-1].price
        self.nav_date = nav.nav_date(self.isin) or self.txns[-1].txn_date

        self.value = self.holding * self.nav

        # Fetch Master Data
        mf_master = self.investor.user.mf_master
        if not mf_master.exists(self.isin):
            mf_master.add_scheme(self.isin,
                                 self.scheme_name,
                                 last_txn_date=self.last_txn.txn_date.strftime('%Y-%m-%d'),
                                 ignore_if_exists=True)

        scheme_data = mf_master.get_scheme(self.isin)
        self.scheme_name = scheme_data.scheme_name
        self.tags = scheme_data.tags
        self.exit_load_days = scheme_data.exit_load_days
        self.ltcg_days = scheme_data.ltcg_days
        self.is_under_asr  = scheme_data.is_under_asr
        self.is_under_stcg = scheme_data.is_under_stcg
        self.is_under_ltcg = scheme_data.is_under_ltcg
        self.compiled_tags = utils.compile_tags(self.tags)

        self.is_asr_only = self.is_under_asr and not self.is_under_ltcg
        self.is_equity   = self.is_under_stcg
        self.is_hybrid   = self.is_under_asr and self.is_under_ltcg
        self.taxation = "Equity" if self.is_equity else "Hybrid" if self.is_hybrid else "Debt"

        self._realized_pnl = 0.0
        self._unrealized_pnl = 0.0

    def _compute_txns_cumulative_balance(self):
        balance = 0
        for txn in self.txns:
            balance += round(balance + txn.units, 4)
            txn.cumm_balance = balance
            if txn.cumm_balance < 0: # This should not happen
                self.is_defective_data = True
                self.defect_desc = f'Cumulative balance is negative for {self.scheme_name} ({self.isin}, '\
                                f'{self.folio}) of {self.investor.name} on {txn.txn_date} '
                break

    def _match_txns(self):
        i_sell = 0     # Loop counter for sell_txns list
        i_buy = 0      # Loop counter for sell_txns list
        matched_txns = []
        if len(self.buy_txns) == 0:
            self.is_defective_data = True
            self.defect_desc = (f'Error: No buy transactions for {self.scheme_name} '
                                f'(isin: {self.isin}, folio: {self.folio}) of {self.investor.name}')
            return self
        while i_sell < len(self.sell_txns):
            sell_txn = self.sell_txns[i_sell]
            # Check for error conditions (These can happen is the data is corrupted)
            if i_buy >= len(self.buy_txns):
                self.is_defective_data = True
                self.defect_desc = (f'Still have unmatched Sold units but Buy txn list overflow while matching txns for'
                                    f' {self.scheme_name} (isin: {self.isin}, folio: {self.folio}) of '
                                    f'{self.investor.name}')
                return self
            buy_txn = self.buy_txns[i_buy]
            if sell_txn.txn_date < buy_txn.txn_date:
                self.is_defective_data = True
                self.defect_desc = (f'Improper ordering or missed txns - Found selling date '
                                    f'{sell_txn.txn_date} to be less than buying date {buy_txn.txn_date} for '
                                    f' {self.scheme_name} (isin: {self.isin}, folio: {self.folio}) of '
                                    f'{self.investor.name}')
                return self

            # Now create next matched_txn
            matched_units = min(sell_txn.unmatched_units, buy_txn.unmatched_units)
            matched_txn = MatchedTxn(self, matched_units, sell_txn, buy_txn)
            # The list for matched_txns is populated here
            matched_txns.append(matched_txn)
            self.buy_txns[i_buy].matched_txns.append(matched_txn)
            self.sell_txns[i_sell].matched_txns.append(matched_txn)

            sell_txn.unmatched_units = round(sell_txn.unmatched_units - matched_units, 4)
            buy_txn.unmatched_units  = round(buy_txn.unmatched_units - matched_units, 4)

            if sell_txn.unmatched_units <= 0: #If all units of this sell txn matched. Move to the next sell txn
                i_sell += 1
            if buy_txn.unmatched_units <= 0: #If all units of this sell txn matched. Move to the next sell txn
                i_buy += 1
        return matched_txns

    def filter(self, hide_before_date=date.today(), selected_cats=None, selected_subs=None):
        c1 = not hide_before_date or (self.holding > 0 or self.last_txn.txn_date > hide_before_date)

        c2_1 = not selected_cats or bool(set(selected_cats) & set(self.compiled_tags.keys()))
        c2_2 = not selected_subs
        if selected_subs:
            for cat, subs in selected_subs.items():
                if cat in self.compiled_tags and len(subs) > 0:
                    if set(subs) & set(self.compiled_tags[cat]):  # common subcategories
                        c2_2 = True
                        break
        # Logic is complex but this seems to be working as desired (19-10-2025)
        c2 = (c2_1 or c2_2) if (selected_cats and selected_subs) else (c2_1 and c2_2)
        return c1 and c2

    def is_sold_in_fy(self, fy):
        for txn in self.sell_txns:
            if utils.is_date_in_fy(txn.txn_date, fy):
                return True
        return False

    def get_realized_pnl(self, fy=None, period=None):
        # get realized return (ASR+STCG+LTCG) for a FY or between 2 dates
        if fy is not None:
            period = utils.get_timeframe(fy=fy) # returns tuple

        if isinstance(period, tuple):   # if period is not None:
            txns = [txn for txn in self.matched_txns if (period[0] <= txn.sell_txn.txn_date <= period[1])]
        else:
            txns = self.matched_txns

        pnl = sum(txn.pnl for txn in txns)
        self.stt = sum(txn.stt for txn in txns)
        self.stamp_duty = sum(txn.stamp_duty for txn in txns)
        return pnl - self.stt - self.stamp_duty

    @property
    def scheme_short_name(self):
        return (self.scheme_name.replace("Plan", "").replace("Fund", "").replace("Scheme", "").
                replace("Growth", "G").replace("  ", " "))

    @property
    def realized_pnl_at_slab_rate(self):
        # Total Realized return liable for Slab Rate Tax
        return self.get_realized_pnl_at_slab_rate()

    @property
    def realized_pnl_at_stcg(self):
        # Total Realized return liable for STCG Tax
        return self.get_realized_pnl_at_stcg()

    @property
    def realized_pnl_at_ltcg(self):
        # Total Realized return liable for LTCG Tax
        return self.get_realized_pnl_at_ltcg()

    @property
    def unrealized_pnl(self):   # This should always be for the current date/FY ??
        # Any property dependent directly or indirectly on NAV is dynamically computed every time
        return sum(txn.unrealized_pnl for txn in self.buy_txns)

    def get_unrealized_pnl(self):   # This should always be for the current date/FY ??
        # Any property dependent directly or indirectly on NAV is dynamically computed every time
        return sum(txn.unrealized_pnl for txn in self.buy_txns)

    def get_total_pnl(self):
        return self.get_realized_pnl() + self.get_unrealized_pnl()

    @property
    def unrealized_tax(self):
        return sum(txn.stamp_duty for txn in self.buy_txns)

    @property
    def total_returns(self):
        return self.realized_pnl[0] + self.unrealized_pnl

    def get_total_returns(self):
        return self.realized_pnl[0] + self.unrealized_pnl

    # @property
    def get_unrealized_pnl_at_slab_rate1(self, load_free=False, fy=None, on_date=None):
        if fy:
            from_dt, to_dt = fy
        on_date = on_date or date.today()
        # Does on_date mean from beginning to this date ??????
        # Should it not be from date and to date always (with None allowed)
        if load_free:
            return sum(txn.unrealized_pnl for txn in self.buy_txns
                       if txn.is_taxable_at_slab_rate_on(on_date) and txn.is_load_free_on(on_date))
        else:
            return sum(txn.unrealized_pnl for txn in self.buy_txns
                       if txn.is_taxable_at_slab_rate_on(on_date))

    def get_unrealized_pnl_at_slab_rate(self, load_free=False, ltcg_after_date=date.today(), load_free_before_date=date.today()):
        # 1. load_free => Should we consider units (buy txn) that are becoming free of exit load before end-of-period
        # 2. ltcg_after_date => Units (buy txn) should not have entered LTCG timeframe before this date
        # 3. load_free_before_date => If load_free flag is True - Units should become load free before the given date
        # Tried to put most logic here instead of relying on functions of BuyTxn object.
        pnl = 0.0
        if self.is_under_asr:
            if load_free:
                pnl = sum(txn.unrealized_pnl for txn in self.buy_txns
                           if txn.ltcg_from_date > ltcg_after_date
                           # and txn.is_load_free_on(load_free_before_date)
                           and txn.load_free_from_date < load_free_before_date
                           )
            else:
                pnl = sum(txn.unrealized_pnl for txn in self.buy_txns
                           if txn.ltcg_from_date > ltcg_after_date)
        return pnl

    @property
    def unrealized_pnl_at_stcg(self):
        return sum(txn.unrealized_pnl for txn in self.buy_txns if txn.is_taxable_at_stcg)

    @property
    def unrealized_pnl_at_ltcg(self):
        return sum(txn.unrealized_pnl for txn in self.buy_txns if txn.is_taxable_at_ltcg)

    @property
    def total_taxes_paid(self):
        return sum(txn.tax for txn in self.txns)

    @property
    def tax_treatment(self):
        return "Equity" if self.is_under_stcg else "Debt" if not self.is_under_ltcg else "Other"

    def realized_xirr(self, fy=None):
        return 0 if len(self.sell_txns) == 0 else xirr(self, realized=True, fy=fy)

    def unrealized_xirr(self):
        return 0 if self.holding == 0 else xirr(self, unrealized=True)

    def total_xirr(self):
        return xirr(self)


    def __iter__(self):
        # Usage - for txn in investment:
        return self.txns



class Txn:
    def __init__(self, investment, txn_rec):
        self.investment = investment
        # self.txn_date = datetime.strptime(txn_date, "%Y-%m-%d").date()
        self.txn_date = utils.normalize_date(txn_rec.date)
        self.units = round(float(txn_rec.quantity), 4)
        self.price = round(float(txn_rec.price), 4)
        self.tax = round(float(txn_rec.tax), 4)
        self.type = None
        self.matched_txns = []
        self.cumm_balance = 0
        self.unmatched_units = abs(self.units)  # For the purpose of using in match_txns logic
        self.value = self.units * self.price + self.tax

class BuyTxn (Txn):
    def __init__(self, investment, txn_rec):
        super().__init__(investment, txn_rec)
        self.type = 'buy'
        self.stamp_duty = self.tax

        # These values can Not be computed when the object is created.
        self._sold_units = 0.0
        self._unrealized_pnl = 0.0
        self._unrealized_pnl_days = 0
        self._unsold_units = 0.0


    @property
    def sold_units(self):
        # Do not use _local_var here. Somehow it gets computed premature and gives wrong results
        # return sum(txn.units for txn in self.matched_txns)
        return self.units - self.unmatched_units

    @property
    def unsold_units(self):
        # Do not use _local_var here. Somehow it gets computed premature and gives wrong results
        return self.unmatched_units

    @property
    def amount(self):
        return (self.price * self.units) + self.tax

    @property
    def sold_amount(self):
        return self.price * self.sold_units + (self.sold_units / self.units * self.tax)

    @property
    def unsold_amount(self):
        return self.price * self.unsold_units + (self.unsold_units / self.units * self.tax)

    @property
    def unsold_value(self):
        return self.unsold_units * self.investment.nav

    @property
    def unrealized_pnl(self):
        # Any property dependent on NAV is dynamically computed every time
        # This value matches with VRO report
        return self.unsold_units * (self.investment.nav - self.price) - (self.unsold_units / self.units * self.tax)

    @property
    def unrealized_pnl_days(self):
        # Any property dependent on NAV is dynamically computed every time
        return (self.investment.nav_date - self.txn_date).days

    @property
    def load_free_from_date(self):
        # try:
        #     return self.txn_date + timedelta(days=self.investment.exit_load_days)
        # except ValueError:
        #     print("Exit load date is Null for: ", self.investment.scheme_name)
        return self.txn_date + timedelta(days=self.investment.exit_load_days)

    @property
    def is_load_free(self):
        return self.is_load_free_within()

    # def is_load_free_on(self, on_date):
    #     return on_date > self.load_free_from_date
    #
    def is_load_free_within(self, from_date=None, to_date=date.today()):
        load_free = True
        if from_date is not None:
            load_free = self.load_free_from_date >= from_date
        if to_date is not None:
            load_free = self.load_free_from_date <= to_date
        return load_free

    @property
    def ltcg_from_date(self):
        return self.txn_date + timedelta(days=self.investment.ltcg_days)

    # 3 types of tax treatment for 'buy' transactions
    @property
    def is_taxable_at_slab_rate(self): # Applicable Slab Rates
        return self.is_taxable_at_slab_rate_on(date.today())
        # return  self.investment.is_slab_rate_applicable and sell_date < self.ltcg_from_date

    def is_taxable_at_slab_rate_on(self, on_date):  # Applicable Slab Rates
        return self.investment.is_under_asr and on_date < self.ltcg_from_date

    @property
    def is_taxable_at_stcg(self, sell_date=date.today()):
        return  self.investment.is_under_stcg and sell_date < self.ltcg_from_date
    @property
    def is_taxable_at_ltcg(self, sell_date=date.today()):
        return  self.investment.is_under_ltcg and sell_date > self.ltcg_from_date

    @property
    def unrealized_cagr(self):
        return cagr(self.unsold_amount, self.unsold_value, self.txn_date, date.today())


class SellTxn (Txn):
    def __init__(self, investment, txn_rec):
        super().__init__(investment, txn_rec)
        self.type = 'sell'
        self.amount = abs((self.price * self.units) + self.tax)
        self._fy = None    # Financial Year
        self.stt = self.tax

        # These values can Not be computed when the object is created.
        self._realized_pnl = 0.0

    # This realized pnl may be a combination of STCG and LTCG
    # For taxation purposes, refer to pnl and tax_type of matched_txns
    @property
    def realized_pnl(self):
        self._realized_pnl = self._realized_pnl or sum(pnl for pnl in self.matched_txns)
        return self._realized_pnl

    @property
    def fy(self):
        self._fy = self._fy or utils.get_fy(self.txn_date)
        return self._fy



class MatchedTxn:
    def __init__(self, investment, units, sell_txn, buy_txn):
        self.investment = investment
        self.units = units
        self.buy_txn = buy_txn
        self.sell_txn = sell_txn
        self._fy = None
        # self.stamp_duty = 0.0
        # self.stt = 0.0
        # Compute taxes
        # self.stamp_duty = round((self.buy_txn.stamp_duty / self.buy_txn.units) * self.units, 2)
        # self.stt        = round((self.sell_txn.stt / self.sell_txn.units) * self.units, 2)
        # self._tax_type = None

    @property
    def stt(self):
        return self.sell_txn.stt * (self.units / self.sell_txn.units)

    @property
    def stamp_duty(self):
        return self.buy_txn.stamp_duty * (self.units / self.buy_txn.units)

    @property
    def tax_amount(self):
        return self.stt + self.stamp_duty

    @property
    def buy_amount(self):
        return self.buy_txn.amount * (self.units / self.buy_txn.units)

    @property
    def sell_amount(self):
        return abs(self.sell_txn.amount * (self.units / self.sell_txn.units))

    @property
    def pnl(self):
        # This value matches with VRO report
        # return self.units * (self.sell_txn.price - self.buy_txn.price) # - self.stt - self.stamp_duty
        return self.sell_amount - self.buy_amount

    @property
    def ltcg(self):
        investment = self.sell_txn.investment
        _ltcg = self.pnl
        if investment.is_under_stcg and investment.is_under_ltcg:   # Equity investment for Grand fathering LTCG
            gf_date = datetime.strptime("2018-01-31", "%Y-%m-%d").date()
            if self.buy_txn.txn_date <= gf_date and self.is_taxable_at_ltcg:
                fmv_31_01_2018 = nav.nav_on_31012018(investment.isin)
                deemed_coa = max(self.buy_txn.price, min(self.sell_txn.price, fmv_31_01_2018))
                _ltcg = (self.sell_txn.price - deemed_coa) * self.units
        return _ltcg

    @property
    def cagr(self):
        return cagr(self.buy_amount, self.sell_amount, self.buy_txn.txn_date, self.sell_txn.txn_date)

    @property
    def sell_date(self):
        return self.sell_txn.txn_date

    @property
    def buy_date(self):
        return self.buy_txn.txn_date

    @property
    def holding_period(self):
        return (self.sell_txn.txn_date - self.buy_txn.txn_date).days

    @property
    def fy(self):
        self._fy = self._fy or utils.get_fy(self.sell_txn.txn_date)
        return self._fy

    @property
    def is_load_free(self):
        return self.buy_txn.is_load_free(self.sell_txn.txn_date)

    # @property
    # def is_slab_rate_applicable(self):
    #     return self.sell_txn.investment.is_under_asr
    # @property
    # def is_stcg_applicable(self):
    #     return self.sell_txn.investment.is_under_stcg
    #
    # @property
    # def is_ltcg_applicable(self):
    #     return self.sell_txn.investment.is_under_ltcg

    @property
    def is_taxable_at_slab_rate(self):
        # If tax_treatment on investment is Slab-Rate and units held for less than LTCG applicable days (for Hybrid)
        if self.investment.is_under_asr:
            if self.investment.is_under_ltcg:
                return self.holding_period < self.investment.ltcg_days
            else:
                return True
        else:
            return False
        # return self.investment.is_under_asr and (self.holding_period < self.sell_txn.investment.ltcg_days)

    @property
    def is_taxable_at_stcg(self):
        return self.investment.is_under_stcg and (self.holding_period < self.investment.ltcg_days)

    @property
    def is_taxable_at_ltcg(self):
        return self.investment.is_under_ltcg and (self.holding_period >= self.investment.ltcg_days)

    @property
    def applicable_tax_treatment(self):
        if self.is_taxable_at_slab_rate:
            tax_treatment = "Slab Rate"
        elif self.is_taxable_at_stcg:
            tax_treatment = "STCG"
        elif self.is_taxable_at_ltcg:
            tax_treatment = "LTCG"
        else:
            tax_treatment = "Error"
        return tax_treatment
