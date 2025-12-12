import streamlit as st
import pandas as pd
from datetime import datetime, date

import utils.utils as utils
import model.nav as nav
import view.options as user_options

class CapitalGainsMain():
    ############# WORK HERE
    def __init__(self, investments):
        self.options = st.session_state.options
        self.investments = investments

    def show_common(self):
        with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="bottom"):
            with st.container():
                st.write(f"#### Capital Gains (FY {self.options.selected_fy})")
                metrics_box = st.popover(f"Summary Metrics", width=200)
            with st.container(horizontal_alignment="right"):
                with st.container(horizontal_alignment="right", horizontal=True):
                    st.caption(f"<div style='text-align: right; font-size: 1rem; color:#279FF5; font-weight:600;"
                               f"margin:-12px 10px 12px 0;'>{self.options.selected_investor_name}</div>",
                               unsafe_allow_html=True, )
                if st.button("Modity filters...", type="secondary") or not self.options.selected_fy:
                    user_options.user_options(select_investor=True, select_fy=True)

        fy = self.options.selected_fy
        sale_value = []
        asr_cg = []
        stcg = []
        ltcg_pnl = []
        for inv in self.investments:
            sale_value.append(sum(txn.sell_amount for txn in inv.matched_txns if txn.fy == fy))
            asr_cg.append(sum(txn.pnl for txn in inv.matched_txns if txn.is_taxable_at_slab_rate and txn.fy == fy)
                            if inv.is_under_asr else 0)
            stcg.append(sum(txn.pnl for txn in inv.matched_txns if txn.is_taxable_at_stcg and txn.fy == fy)
                            if inv.is_under_stcg else 0)
            ltcg_pnl.append(sum(txn.ltcg for txn in inv.matched_txns if txn.is_taxable_at_ltcg and txn.fy == fy)
                            if inv.is_under_ltcg else 0)

        cols = metrics_box.columns(4, gap="small", width=800)
        cols[0].metric(label="Investments #",
                       value=utils.number_str(len(self.investments)),
                       help=f"Number of investments having redemptions in FY {self.options.selected_fy}",)
        cols[1].metric(label="ASR Gain",
                       value=utils.number_str(sum(asr_cg), 2, compact="L"),
                       help="Total gains taxable at applicable slab rates: ₹"+utils.number_str(sum(asr_cg),))
        cols[2].metric(label="STCG",
                       value=utils.number_str(sum(stcg), 2, compact="L"),
                       help="Total gains taxable at STCG rates: ₹"+utils.number_str(sum(stcg),))
        cols[3].metric(label="LTCG",
                       value=utils.number_str(sum(ltcg_pnl), 2, compact="L"),
                       help="Total LTCG before applying GrandFathering: ₹"+utils.number_str(sum(ltcg_pnl),))

        # st.markdown("---")
        # st.markdown(
        #     "<hr style='border: 0.7px solid rgba(0,0,0,0.1); margin-top: -10px; margin-bottom: -20px'>",
        #     unsafe_allow_html=True
        # )
        return self

class CGInvestments:
    def __init__(self, investments):
        self.options = st.session_state.options
        self.investments = investments
        self.selected_investment = None

    def prepare_report(self):
        # investments = self.investor.get_filtered_investments(
        #     sold_in_fy=self.options.selected_fin_year
        # )
        fy = self.options.selected_fy
        sale_value = []
        asr_cg = []
        stcg = []
        ltcg = []
        tax_treatment = []
        for inv in self.investments:
            sale_value.append(sum(txn.sell_amount for txn in inv.matched_txns if txn.fy == fy))
            asr_cg.append(sum(txn.pnl for txn in inv.matched_txns if txn.is_taxable_at_slab_rate and txn.fy == fy)
                            if inv.is_under_asr else 0)
            stcg.append(sum(txn.pnl for txn in inv.matched_txns if txn.is_taxable_at_stcg and txn.fy == fy)
                            if inv.is_under_stcg else 0)
            ltcg.append(sum(txn.ltcg for txn in inv.matched_txns if txn.is_taxable_at_ltcg and txn.fy == fy)
                            if inv.is_under_ltcg else 0)
            # tax_treatment.append("Equity" if inv.is_under_stcg else "Debt" if not inv.is_under_ltcg else "Other")
            tax_treatment.append(inv.tax_treatment)

        df1 = pd.DataFrame({
            'inv_index': range(len(self.investments)),
            'tax_treatment': tax_treatment,
            "sale_value": sale_value,
            "asr_cg": asr_cg,
            "stcg": stcg,
            "ltcg": ltcg,
        })
        tax_treatment_type = pd.CategoricalDtype(categories=["Debt", "Other", "Equity"],
                                                 ordered=True);df1["investments"] = [f"{i.scheme_name} /{i.folio}"
                                                                                     for i in self.investments]
        df1["tax_treatment"] = df1["tax_treatment"].astype(tax_treatment_type)

        df1.set_index(["investments"], inplace=True)
        df1.sort_values(by=["tax_treatment", "investments"], ascending=[True, True], inplace=True)

        # def format_tab1(self):
        formatted_df1 = df1.style.format(utils.number_str, subset = ["asr_cg", "stcg", "ltcg", "sale_value"],)

        column_config_df1 = {
            "tax_treatment": st.column_config.Column(
                label="Tax Treatment", width="small", help="Tax treatment for the scheme"
            ),
            "sale_value": st.column_config.Column(
                label="Sale Amount", width="small", help="Total sold amount during selected FY"
            ),
            "asr_cg": st.column_config.Column(
                label="ASR Gain", width="small", help="Gains taxable at 'Applicable Slab Rates'"
            ),
            "stcg": st.column_config.Column(
                label="STCG", width="small", help="Gains taxable as STCG"
            ),
            "ltcg": st.column_config.Column(
                label="LTCG", width="small", help="Gains taxable as LTCG"
            ),
            "investments": st.column_config.Column(
                label=f"Investments ({len(self.investments)})", width=350,
                help=f"Showing investments having redemptions in FY {self.options.selected_fy}",
            ),
        }

        # if "drill_down_flag" not in st.session_state:
        #     st.session_state.drill_down_flag = False
        #
        cg_df_event = st.dataframe(
            formatted_df1,
            selection_mode=["single-row"],
            on_select="rerun", # if st.session_state.drill_down_flag else "ignore",
            key="cg_df_event",
            column_config=column_config_df1,
            column_order=["investments", "tax_treatment", "sale_value", "asr_cg", "stcg", "ltcg", ],
        )

        try:
            selected_rows = cg_df_event["selection"]["rows"]
            inv_index = df1.iloc[selected_rows[0]]["inv_index"]
            self.selected_investment = self.investments[inv_index]
            st.caption(f"<div style='text-align: left;'>"
                       f"{self.selected_investment.scheme_name} /{self.selected_investment.folio}"
                       f"</div>",
                       unsafe_allow_html=True,
                       )
        except Exception as e:
            selected_rows = []

        # st.toggle("Drill down report", key="drill_down_flag")
        # if st.session_state.drill_down_flag and not selected_rows:
        if not selected_rows:
            st.caption("Select an investment for transaction level details")

        return self

class CGSellTxns:
    def __init__(self, investment,):
        # self.investor = investor
        self.investment = investment
        self.options = st.session_state.options

    def txns_report(self):
        # Slab Rate (debt) PnL for selected FY
        fy = self.options.selected_fy
        sell_txns = [txn for txn in self.investment.sell_txns if txn.fy == fy]
        asr_gain = []
        stcg = []
        ltcg = []
        buy_amount = []
        for sell_txn in sell_txns:
            asr_gain.append(sum(txn.pnl for txn in sell_txn.matched_txns if txn.is_taxable_at_slab_rate))
            stcg.append(sum(txn.pnl for txn in sell_txn.matched_txns if txn.is_taxable_at_stcg))
            ltcg.append(sum(txn.ltcg for txn in sell_txn.matched_txns if txn.is_taxable_at_ltcg))
            buy_amount.append(sum(txn.buy_amount for txn in sell_txn.matched_txns))
        df = pd.DataFrame({
            "sell_date": [txn.txn_date for txn in sell_txns],
            "sell_value": [txn.amount for txn in sell_txns],
            "buy_amount": buy_amount,
            "asr_gain": asr_gain,
            "stcg": stcg,
            "ltcg": ltcg,
        })
        formatted_df = df.style.format(utils.number_str,
           subset = ["asr_gain", "stcg", "ltcg", "sell_value", "buy_amount", "asr_gain", "stcg", "ltcg"],)

        column_config_df = {
            "sell_date": st.column_config.DateColumn(label="Sell Date", format="DD-MMM-YYYY", width=90,),
            "sell_value": st.column_config.Column(
                label="Sale Amount", width="small", help="Redemption Amount"
            ),
            "buy_amount": st.column_config.Column(
                label="Buy Amount", width="small", help="Purchase amount of redeemed units"
            ),
            "asr_gain": st.column_config.Column(
                label="ASR Gain", width="small", help="Gains taxable at 'Applicable Slab Rates'"
            ),
            "stcg": st.column_config.Column(
                label="STCG", width="small", help="Gains taxable as STCG"
            ),
            "ltcg": st.column_config.Column(
                label="LTCG", width="small", help="Gains taxable as LTCG"
            ),
        }

        st.dataframe(formatted_df, column_config=column_config_df, hide_index=True)
        return self

class CGMatchedTxns:
    def __init__(self, investment,):
        # self.investor = investor
        self.investment = investment
        self.options = st.session_state.options

    def txns_report(self):
        # Sell Date | Units | Price | Sell Amount | Buy Date | Price | Buy Amount | ASR Gain | STCG | LTCG
        fy = self.options.selected_fy
        txns = [txn for txn in self.investment.matched_txns if txn.fy == fy]

        df = pd.DataFrame({
            "sell_date": [txn.sell_txn.txn_date for txn in txns],
            "units": [txn.units for txn in txns],
            "sell_price": [txn.sell_txn.price for txn in txns],
            "sell_amount": [txn.sell_amount for txn in txns],
            "buy_date": [txn.buy_txn.txn_date for txn in txns],
            "buy_price": [txn.buy_txn.price for txn in txns],
            "buy_amount": [txn.buy_amount for txn in txns],
            "duration": [txn.holding_period for txn in txns],
            "asr_gain": [(txn.pnl if txn.is_taxable_at_slab_rate else 0) for txn in txns ],
            "stcg"    : [(txn.pnl if txn.is_taxable_at_stcg else 0) for txn in txns],
            "ltcg"    : [(txn.ltcg if txn.is_taxable_at_ltcg else 0) for txn in txns],
            # "gain_type": ["ASR" if txn.is_taxable_at_slab_rate else "STCG" if txn.is_taxable_at_stcg else "LTCG"
            #               for txn in txns],
            # "gain": [txn.pnl for txn in txns],
            # "quarter": quarter,
        })
        formatted_df = (df.style.format(utils.number_str,
                        subset = ["asr_gain", "stcg", "ltcg", "sell_amount", "buy_amount",],)
                        .format(lambda x: utils.number_str(x,4),
                                subset = ["units", "sell_price", "buy_price"],)
                        .format(lambda x: utils.number_str(x,)+" days", subset=[ "duration"])
                        )


        column_config_df = {
            "sell_date": st.column_config.DateColumn(label="Sell Date", format="DD-MMM-YYYY", width=90,),
            "units": st.column_config.Column(
                label="Units", width="small", help="Number of sold units matched with buy transaction"
            ),
            "sell_price": st.column_config.Column(
                label="Sale Price", width="small", help="Redemption NAV"
            ),
            "sell_amount": st.column_config.Column(
                label="Sale Amount", width="small", help="Sale amount of matched units"
            ),
            "buy_date": st.column_config.DateColumn(label="Buy Date", format="DD-MMM-YYYY", width=90,),
            "buy_price": st.column_config.Column(
                label="Buy Price", width="small", help="Purchase NAV"
            ),
            "buy_amount": st.column_config.Column(
                label="Buy Amount", width="small", help="Purchase amount of matched units"
            ),
            "duration": st.column_config.Column(
                label="Duration", width="small", help="Holding period in days"
            ),
            "asr_gain": st.column_config.Column(
                label="ASR Gain", width="small", help="Gains taxable at 'Applicable Slab Rates'"
            ),
            "stcg": st.column_config.Column(
                label="STCG", width="small", help="Gains taxable as STCG"
            ),
            "ltcg": st.column_config.Column(
                label="LTCG", width="small", help="Gains taxable as LTCG"
            ),
        }

        # Drop any of these columns if it is all zeros or blank
        if df["asr_gain"].fillna(0).eq(0).all():
            df.drop("asr_gain", axis=1, inplace=True)
        if df["stcg"].fillna(0).eq(0).all():
            df.drop("stcg", axis=1, inplace=True)
        if df["ltcg"].fillna(0).eq(0).all():
            df.drop("ltcg", axis=1, inplace=True)

        st.dataframe(formatted_df, column_config=column_config_df, hide_index=True)
        return self

class CGQuarterly:
    def __init__(self, investments):
        self.options = st.session_state.options
        self.selected_gain_type = None
        self.investments = investments

    def consolidated_df(self):
        fy = self.options.selected_fy
        sell_amount = {"asr": 0.0, "ltcg": 0.0, "stcg": 0.0,}
        buy_amount = {"asr": 0.0, "ltcg": 0.0, "stcg": 0.0,}
        total_gain = {"asr": 0.0, "ltcg": 0.0, "stcg": 0.0,}
        quarterly_gain = []     # List of Dicts
        for qtr in range(5):
            # Quarters are based upon 5 advance Tax deposit dates of income tax (as per IT form)
            # Create 5 buckets (date windows) for ASR, STCG & LTCG
            quarterly_gain.append({
                "from_date": utils.fy_qtr_start_date(fy, qtr+1),
                "to_date"  : utils.fy_qtr_end_date(fy, qtr+1),
                "asr_gain" : 0.0,
                "stcg"     : 0.0,
                "ltcg"     : 0.0,
            })

        for qtr in range(5):
            # Fetch gains at investment/txn level and add to quarterly window
            from_date = quarterly_gain[qtr]["from_date"]
            to_date = quarterly_gain[qtr]["to_date"]
            for investment in self.investments:
                # Filter on txns for current quarter dates window
                txns_in_quarter = [txn for txn in investment.matched_txns
                                   if from_date <= txn.sell_txn.txn_date <= to_date]
                if not txns_in_quarter:
                    continue

                if investment.is_under_asr:
                    asr_gain_txns = [txn for txn in txns_in_quarter if txn.is_taxable_at_slab_rate]
                    quarterly_gain[qtr]["asr_gain"] += sum(txn.pnl for txn in asr_gain_txns)
                    sell_amount["asr"] += sum(txn.sell_amount for txn in asr_gain_txns)
                    buy_amount["asr"]  += sum(txn.buy_amount for txn in asr_gain_txns)
                    total_gain["asr"]  += sum(txn.pnl for txn in asr_gain_txns)

                if investment.is_under_stcg:
                    stcg_txns = [txn for txn in txns_in_quarter if txn.is_taxable_at_stcg]
                    quarterly_gain[qtr]["stcg"] += sum(txn.pnl for txn in stcg_txns)
                    sell_amount["stcg"] += sum(txn.sell_amount for txn in stcg_txns)
                    buy_amount["stcg"]  += sum(txn.buy_amount for txn in stcg_txns)
                    total_gain["stcg"]  += sum(txn.pnl for txn in stcg_txns)

                if investment.is_under_ltcg:
                    ltcg_txns = [txn for txn in txns_in_quarter if txn.is_taxable_at_ltcg]
                    quarterly_gain[qtr]["ltcg"] += sum(txn.ltcg for txn in ltcg_txns) #txn.ltcg() takes care of GrandFathering
                    sell_amount["ltcg"] += sum(txn.sell_amount for txn in ltcg_txns)
                    buy_amount["ltcg"]  += sum(txn.buy_amount for txn in ltcg_txns)
                    total_gain["ltcg"]  += sum(txn.ltcg for txn in ltcg_txns) #txn.ltcg() takes care of GrandFathering

        df1 = pd.DataFrame({})
        df1["gain_type"] = ("ASR - Gains Taxable at Applicable Slab Rate",
                            "STCG - Short Term Capital Gains Taxable @20%",
                            "LTCG - Long Term Capital gains taxable @12.5%",
                           )
        df1["sell_value"] = (sell_amount["asr"], sell_amount["stcg"], sell_amount["ltcg"])
        df1["buy_value"]  = (buy_amount["asr"], buy_amount["stcg"], buy_amount["ltcg"])
        df1["total_gain"] = (total_gain["asr"], total_gain["stcg"], total_gain["ltcg"])
        for qtr in range(5):
            # Create columns for quarters
            df1[f"Q{qtr+1}"] = (quarterly_gain[qtr]["asr_gain"], quarterly_gain[qtr]["stcg"], quarterly_gain[qtr]["ltcg"])

        df1.set_index(["gain_type"], inplace=True)

        formatted_df1 = df1.style.format(utils.number_str)
        column_config_df1 = {
            "gain_type": st.column_config.Column(
                label="Capital Gain type", help="Capital Gain type", width=350,
            ),
            "sell_value": st.column_config.Column(
                label="Value", width="small", help="Total Sale Value"
            ),
            "buy_value": st.column_config.Column(
                label="Cost", width="small", help="Total Purchase Cost"
            ),
            "total_gain": st.column_config.Column(
                label="Capital Gain", width="small", help="Total Gain in FY"
            ),
        }
        for qtr in range(5):
            column_config_df1[f"Q{qtr+1}"] = st.column_config.Column(
                label=f"Q{qtr+1} ({quarterly_gain[qtr]['to_date'].strftime('%d-%b')})",
                width="small",
                help=f"Gains from {quarterly_gain[qtr]['from_date'].strftime('%d-%b-%Y')} to "
                     f"{quarterly_gain[qtr]['to_date'].strftime('%d-%b-%Y')}",
            )

        if "show_investments_flag" not in st.session_state:
            st.session_state.show_investments_flag = False

        consolidated_df_event = st.dataframe(formatted_df1,
                     selection_mode=["single-row"],
                     on_select="rerun", # if st.session_state.show_investments_flag else "ignore",
                     key="consolidated_df_event",
                     column_config=column_config_df1)
        try:  # When on_select = "ignore", consolidated_df_event is not unsubscripted
            selected_rows = consolidated_df_event["selection"]["rows"]
            self.selected_gain_type = ["ASR", "STCG", "LTCG"][selected_rows[0]]
            # print(self.selected_gain_type)
        except Exception:
            selected_rows = []

        # st.toggle("Drill down report", key="show_investments_flag")
        # if st.session_state.show_investments_flag and not selected_rows:
        if not selected_rows:
            st.caption("Select a row for investment level details")
        else:
            st.caption(f"<div style='text-align: left; font-size: 1rem'>"
                         f"{df1.index[selected_rows[0]]}"
                         f"</div>",
                         unsafe_allow_html=True,
                         )

        return self

class CGQuarterlyInvestments:
    def __init__(self, investments, gain_type):
        self.options = st.session_state.options
        self.gain_type = gain_type
        self.investments = investments
        self.selected_investment = None

    def investments_df(self):
        # investments = self.investor.get_filtered_investments(
        #     sold_in_fy=self.options.selected_fy
        # )
        fy = self.options.selected_fy
        if "show_txns_flag" not in st.session_state:
            st.session_state.show_txns_flag = False

        indices = []
        tax_treatment = []
        sale_amount = []
        buy_amount = []
        total_gain = []
        quarterly_gain = []
        for qtr in range(5):
            quarterly_gain.append({
                "from_date": utils.fy_qtr_start_date(fy, qtr+1),
                "to_date": utils.fy_qtr_end_date(fy, qtr+1),
                "gains": [],
            })

        eligible_investments = []
        for investment in self.investments:
            txns = []
            if self.gain_type == "ASR" and investment.is_under_asr:
                txns = [txn for txn in investment.matched_txns if txn.fy == fy and txn.is_taxable_at_slab_rate]
            elif self.gain_type == "STCG" and investment.is_under_stcg:
                txns = [txn for txn in investment.matched_txns if txn.fy == fy and txn.is_taxable_at_stcg]
            elif self.gain_type == "LTCG" and investment.is_under_ltcg:
                txns = [txn for txn in investment.matched_txns if txn.fy == fy and txn.is_taxable_at_ltcg]

            if not any(txns):
                # Skip loop if investment is of not selected_gain_type or no sell transactions in FY
                continue
            eligible_investments.append(investment)
            indices.append(f"{investment.scheme_name} /{investment.folio} ({investment.tax_treatment})")
            tax_treatment.append(investment.tax_treatment)
            sale_amount.append(sum(txn.sell_amount for txn in txns))
            buy_amount.append(sum(txn.buy_amount for txn in txns))
            total_gain.append(sum((txn.ltcg if self.gain_type == "LTCG" else txn.pnl) for txn in txns))
            for qtr in range(5):
                from_date = quarterly_gain[qtr]["from_date"]
                to_date = quarterly_gain[qtr]["to_date"]
                quarterly_gain[qtr]["gains"].append(sum((txn.ltcg if self.gain_type == "LTCG" else txn.pnl)
                                            for txn in txns if from_date <= txn.sell_txn.txn_date <= to_date))

        df1 = pd.DataFrame({})
        df1["investment"] = indices
        df1["tax_treatment"] = tax_treatment
        df1["sale_value"]  = sale_amount
        df1["buy_value"] = buy_amount
        df1["total_gain"] = total_gain

        for qtr in range(5):
            df1[f"Q{qtr+1}"] = quarterly_gain[qtr]["gains"]

        df1.set_index(["investment"], inplace=True)

        formatted_df1 = df1.style.format(utils.number_str)

        column_config_df1 = {
            "investment": st.column_config.Column(
                label=f"Investments ({len(indices)})",
                help=f"Investments with gains at {self.gain_type}",
                width=350 if st.session_state.show_txns_flag else 382,
            ),
            "tax_treatment": st.column_config.Column(
                label="Taxation Type", width="small", help="How this investment is taxed"
            ),
            "sale_value": st.column_config.Column(
                label="Value", width="small", help="Total Sale Value"
            ),
            "buy_value": st.column_config.Column(
                label="Cost", width="small", help="Total Purchase Cost"
            ),
            "total_gain": st.column_config.Column(
                label="Total Gain", width="small", help="Total Gain in FY"
            ),
        }
        for qtr in range(5):
            column_config_df1[f"Q{qtr+1}"] = st.column_config.Column(
                # label=f"Q{qtr+1} ({quarterly_gain[qtr]['to_date'].strftime('%d-%b-%Y')})",
                width="small",
                help=f"Gains from {quarterly_gain[qtr]['from_date'].strftime('%d-%b-%Y')} to "
                     f"{quarterly_gain[qtr]['to_date'].strftime('%d-%b-%Y')}",
            )

        investments_df_event = st.dataframe(formatted_df1,
                     selection_mode=["single-row"],
                     on_select="rerun", # if st.session_state.show_txns_flag else "ignore",
                     key="investments_df_event",
                     column_config=column_config_df1)
        try:  # When on_select = "ignore", investments_df_event is not unsubscripted
            selected_rows = investments_df_event["selection"]["rows"]
            self.selected_investment = eligible_investments[selected_rows[0]]
        except Exception:
            selected_rows = []

        # st.toggle("Show transactions", key="show_txns_flag")
        # if st.session_state.show_txns_flag and not selected_rows:
        if not selected_rows:
            st.caption("Select a row for transaction level details")

        return self

class CGQuarterlyTransactions:
    def __init__(self, investment, gain_type="ASR"):
        self.investment = investment
        self.options = st.session_state.options
        self.gain_type = gain_type

    def transactions_df(self):
        # Sell Date | Units | Price | Sell Amount| Buy Date | Price | Buy Amount | Gain Type | Gain ₹ | Quarter
        fy = self.options.selected_fy

        txns = [txn for txn in self.investment.matched_txns if txn.fy == fy]

        quarter = []
        from_date = [None] * 5
        to_date = [None] * 5
        for qtr in range(5):
            from_date[qtr] = utils.fy_qtr_start_date(fy, qtr+1)
            to_date[qtr] = utils.fy_qtr_end_date(fy, qtr+1)
        for txn in txns:
            for qtr in range(5):
                if from_date[qtr] <= txn.sell_txn.txn_date <= to_date[qtr]:
                    quarter.append(f"Q{qtr + 1}")

        df1 = pd.DataFrame({
            "sell_date": [txn.sell_txn.txn_date for txn in txns],
            "units": [txn.units for txn in txns],
            "sell_price": [txn.sell_txn.price for txn in txns],
            "sell_amount": [txn.sell_amount for txn in txns],
            "buy_date": [txn.buy_txn.txn_date for txn in txns],
            "buy_price": [txn.buy_txn.price for txn in txns],
            "buy_amount": [txn.buy_amount for txn in txns],
            "duration": [txn.holding_period for txn in txns],
            "gain_type": ["ASR" if txn.is_taxable_at_slab_rate else "STCG" if txn.is_taxable_at_stcg else "LTCG"
                          for txn in txns],
            "gain": [(txn.ltcg
                     if (self.investment.tax_treatment.lower() == "equity" and txn.is_taxable_at_ltcg)
                      else txn.pnl)
                     for txn in txns],
            "quarter": quarter,
        })

        formatted_df1 = df1.style.format(
            utils.number_str, subset=["sell_amount", "buy_amount", "gain", "duration"]
        ).format(
            lambda x: utils.number_str(x, 4),
            subset=["units", "sell_price", "buy_price"]
        ).format(
            lambda x: utils.number_str(x)+" days", subset=["duration"]
        )

        column_config_df1 = {
            "sell_date": st.column_config.DateColumn(label="Sell Date", format="DD-MMM-YYYY", width=90,),
            "units": st.column_config.Column(label="Units", width="small",),
            "sell_price": st.column_config.Column(label="Sale Price", width="small",),
            "sell_amount": st.column_config.Column(label="Sale Amount", width="small",),
            "buy_date": st.column_config.DateColumn(label="Buy Date", format="DD-MMM-YYYY", width=90,),
            "buy_price": st.column_config.Column(label="Buy Price", width="small",),
            "buy_amount": st.column_config.Column(label="Buy Amount", width="small",),
            "duration": st.column_config.Column(label="Duration", width="small", help="Holding period in days"),
            "gain_type": st.column_config.Column(label="Taxability", width="small",),
            "gain": st.column_config.Column(label="Capital Gain", width="small",),
            "quarter": st.column_config.Column(label="Quarter", width="small", help="Advance Tax Payment Quarter"),
        }

        st.caption(f"<div style='text-align: left;'>"
                   f"{self.investment.scheme_name}"
                   f"</div>",
                   unsafe_allow_html=True,
                   )
        st.dataframe(formatted_df1, column_config=column_config_df1, hide_index=True)

        return self

class Section112A:
    def __init__(self, investments):
        self.options = st.session_state.options
        self.investments = investments
        self.selected_investment = None
        self.applicable_ltcg = None

    def show_report(self):
        # A. Units purchased before 31-01-2018
        # Investment | ISIN | Sale Date | Units | Sale Price | Sale Amount | Buy Date | Buy Price | Buy Amount | FMV @31.01.2018 | Deemed COA | LTCG
        # Deemed COA (cost of acquisition) = max(buy Price, min(Sale Price, FMV @31.01.2018))
        # LTCG = (Sale Price - Deemed COA) x Units

        # B. Units purchased after 31-01-2018
        # Sale Consideration | Cost of acquisition | Expenses | LTCG

        gf_date = datetime.strptime("2018-01-31", "%Y-%m-%d").date()
        fy = self.options.selected_fy
        # investments = self.investor.get_filtered_investments(sold_in_fy=self.options.selected_fy)
        investments = [investment for investment in self.investments if investment.is_under_ltcg]

        txns = []
        for investment in investments:
            # All units eligible for LTCG that were sold in current FY but bought before GF date
            txns += [txn for txn in investment.matched_txns
                     if txn.fy == fy and txn.buy_date <= gf_date and txn.is_taxable_at_ltcg]

        units = [txn.units for txn in txns]
        sale_price = [txn.sell_txn.price for txn in txns]
        buy_price = [txn.buy_txn.price for txn in txns]
        pnl = [txn.pnl for txn in txns]

        fmv_31_01_2018 = [nav.nav_on_31012018(txn.sell_txn.investment.isin) for txn in txns]
        deemed_coa = [max(cp, min(sp, fmv)) for cp, sp, fmv in zip(buy_price, sale_price, fmv_31_01_2018)]
        # ltcg = [(sp - coa)* u for sp, coa, u in zip(sale_price, deemed_coa, units)]

        df1 = pd.DataFrame({
            "sequence": [i+1 for i in range(len(txns))],
            "investment": [f"{txn.sell_txn.investment.scheme_name} /{txn.sell_txn.investment.folio}" for txn in txns],
            "isin"      : [txn.sell_txn.investment.isin for txn in txns],
            "sale_date" : [txn.sell_date for txn in txns],
            "units"     : units,
            "sale_price": sale_price,
            "sale_amount": [txn.sell_amount for txn in txns],
            "buy_date"  : [txn.buy_date for txn in txns],
            "buy_price" : buy_price,
            "buy_amount": [txn.buy_amount for txn in txns],
            "pnl": [txn.pnl for txn in txns],
            "fmv_31_01_2018": fmv_31_01_2018,
            "deemed_coa": deemed_coa,
            "ltcg":     [txn.ltcg for txn in txns],
            # "ltcg1": ltcg,
        })
        df1.set_index(["sequence", "investment"], inplace=True)
        formatted_df1 = (df1.style.format(utils.number_str,
                        subset = ["sale_amount", "buy_amount", "ltcg", "pnl"],)
                        .format(lambda x: utils.number_str(x,4),
                                subset = ["units", "sale_price", "buy_price", "fmv_31_01_2018", "deemed_coa"],)
                        )
        column_config_df1 = {
            "sequence": st.column_config.Column(
                label="#", width=28, help="Row sequence number"
            ),
            "investment": st.column_config.Column(
                label="Investment", width=300, help="Investments with purchase date earlier than 01-Feb-1018"
            ),
            "isin": st.column_config.Column(
                label="ISIN", width="small", help="Required for filling ITR Section 112A"
            ),
            "sale_date": st.column_config.DateColumn(label="Sale Date", format="DD-MMM-YYYY", width=90,),
            "units": st.column_config.Column(
                label="Units", width="small", help="Number of sold units matched with buy transaction"
            ),
            "sale_price": st.column_config.Column(
                label="Sale Price", width="small", help="Redemption NAV"
            ),
            "sale_amount": st.column_config.Column(
                label="Sale Amount", width="small", help="Sale amount of matched units"
            ),
            "buy_date": st.column_config.DateColumn(label="Buy Date", format="DD-MMM-YYYY", width=90,),
            "buy_price": st.column_config.Column(
                label="Buy Price", width="small", help="Purchase NAV"
            ),
            "buy_amount": st.column_config.Column(
                label="Buy Amount", width="small", help="Purchase amount of matched units"
            ),
            "pnl": st.column_config.Column(
                label="P&L", width="small", help="P&L"
            ),
            "fmv_31_01_2018": st.column_config.Column(
                label="FMV @31.01.2018", width="small", help="NAV on 31-Jan-2018"
            ),
            "deemed_coa": st.column_config.Column(
                label="Deemed COA", width="small", help="Deemed Cost of Acquisition max(CP, min(SP, FMV)"
            ),
            "ltcg": st.column_config.Column(
                label="LTCG", width="small", help="Gains taxable as LTCG = (SP - COA) * Units"
            ),
        }

        st.caption(f"<div style='text-align: left;'>"
                   f"LTCG for units bought before 01-Feb-2018"
                   f"</div>",
                   unsafe_allow_html=True,
                   )
        st.dataframe(formatted_df1, column_config=column_config_df1)

        col1, col2, col3, col4 = st.columns(4)
        df1.reset_index(inplace=True)
        col1.metric("Investments #", value=df1["investment"].nunique(),
                  help="Number of investments where purchase was made before 01-Feb-2018")
        col2.metric("Sale Txns #", value=len(df1[["investment", "sale_date"]].drop_duplicates()),         #value=sale_txns_count,
                  help="Number of Sale transactions where purchase was made before 01-Feb-2018")
        col3.metric("P&L", value="₹"+utils.number_str(sum(pnl)),
                  help="Number of matched transactions where purchase was made before 01-Feb-2018")
        # col3.metric("Matched Txns #", value=len(df1['ltcg']),
        #           help="Number of matched transactions where purchase was made before 01-Feb-2018")
        ltcg_gf_txns = sum(df1["ltcg"])
        col4.metric("LTCG", value="₹"+utils.number_str(ltcg_gf_txns),
                  help="Total LTCG for transactions where purchase was made before 01-Feb-2018")


        st.caption(f"<div style='text-align: left;'>"
                   f"LTCG for units bought on or after 01-Feb-2018"
                   f"</div>",
                   unsafe_allow_html=True,
                   )

        txns = []
        index = []
        sale_amount = []
        buy_amount = []
        ltcg = []
        tax_treatment = []
        for investment in investments:
            txns = [txn for txn in investment.matched_txns if txn.fy == fy and txn.buy_date > gf_date and txn.is_taxable_at_ltcg]
            if txns:
                index.append(f"{investment.scheme_name} /{investment.folio}")
                sale_amount.append(sum([txn.sell_amount for txn in txns]))
                buy_amount.append(sum([txn.buy_amount for txn in txns]))
                ltcg.append(sum([txn.ltcg for txn in txns]))
                tax_treatment.append(investment.tax_treatment)

        col1, col2, col3, col4 = st.columns(4)
        df1.reset_index(inplace=True)
        col1.metric("Investments #", value=len(index),
                  help="Number of investments where purchase was made on/after 01-Feb-2018")
        col2.metric("Sale Consideration", value="₹"+utils.number_str(sum(sale_amount)),
                  help="Number of Sale transactions where purchase was made after 01-Feb-2018")
        col3.metric("Purchase Cost", value="₹"+utils.number_str(sum(buy_amount)),
                  help="Number of matched transactions where purchase was made after 01-Feb-2018")
        col4.metric("LTCG", value="₹"+utils.number_str(sum(ltcg)),
                  help="Total LTCG for transactions where purchase was made after 01-Feb-2018")
        ltcg_non_gf_txns = sum(ltcg)
        df2 = pd.DataFrame({
            "sequence": [i+1 for i in range(len(index))],
            "investment": index,
            "tax_treatment": tax_treatment,
            "sale_amount": sale_amount,
            "buy_amount": buy_amount,
            "ltcg": ltcg,
        })

        df1.set_index(["sequence", "investment"], inplace=True)
        df2.sort_values(by=["tax_treatment", "investment"], ascending=[True, True], inplace=True)
        st.dataframe(df2, hide_index=True)

        self.applicable_ltcg = ltcg_gf_txns + ltcg_non_gf_txns

        return self


def capital_gains():
    options = st.session_state.options
    if not options.selected_investor_name or not options.selected_fy:
        user_options.user_options(select_investor=True, select_fy=True)
    investor = st.session_state.user.investors[options.selected_investor_name]
    investments = [investment for investment in investor.investments
                   if investment.is_sold_in_fy(options.selected_fy)
                   ]
    investments.sort(key=lambda investment: investment.scheme_name)
    # return investments

    cg_main = CapitalGainsMain(investments)
    cg_main.show_common()

    tabs = st.tabs(["Capital Gains", "Quarterly", "112A",] )
    with tabs[0]:
        cg_report = CGInvestments(investments)
        cg_report.prepare_report()

        if cg_report.selected_investment:
            tab1, tab2, tab3 = st.tabs(["Sale Transactions", "Buy-Sell Matched Transactions", "Unsold Buy Transactions"])
            with tab1:
                transactions = CGSellTxns(cg_report.selected_investment)
                transactions.txns_report()
            with tab2:
                transactions = CGMatchedTxns(cg_report.selected_investment)
                transactions.txns_report()

    with tabs[1]:
        consolidated = CGQuarterly(investments)
        consolidated.consolidated_df()

        if consolidated.selected_gain_type:
            cg_investments = CGQuarterlyInvestments(investments, consolidated.selected_gain_type,)
            cg_investments.investments_df()

            if cg_investments.selected_investment:
                transactions = CGQuarterlyTransactions(cg_investments.selected_investment)
                transactions.transactions_df()
    with tabs[2]:
        report_112A = Section112A(investments)
        report_112A.show_report()
        # cg_main.ltcg_metric_col.metric("Applicable LTCG", value=utils.number_str(report_112A.applicable_ltcg, 2, compact="L"))
    return

capital_gains()
# cg_main = CapitalGainsMain()
# cg_main.show_common()
