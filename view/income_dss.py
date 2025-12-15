import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta

import view.options as user_options
import utils.utils as utils


class RedemptionsDSS:
    def __init__(self, tax_type):
        self.options = st.session_state.options
        self.tax_type = tax_type
        if not self.options.selected_investor_name:
            user_options.user_options(select_investor=True,)
        self.investor = st.session_state.user.investors[self.options.selected_investor_name]
        # Only one investor is allowed to be selected for this report
        investor = st.session_state.user.investors[self.options.selected_investor_name]
        self.investments = []
        for investment in investor.investments:
            if ((investment.is_sold_in_fy(utils.current_fy()) or investment.holding > 0) and
                    ((investment.is_under_asr and self.tax_type == "ASR") or
                    (investment.is_under_stcg and self.tax_type == "STCG"))
                ):
                self.investments.append(investment)

        self.investments.sort(key=lambda investment: investment.scheme_name)

        self.selected_investment = None
        self.as_on_date = None

    def show(self):
        with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="bottom"):
            st.write(f"#### Redemption Guide for {'ASR Income' if self.tax_type=='ASR' else 'Capital Gains'} "
                     f"(FY {self.options.selected_fy})")
            # with st.container(horizontal_alignment="right", horizontal=True):
            st.caption(f"<div style='text-align: right; font-size: 1rem; color:#279FF5; font-weight:600;"
                       f"margin:-12px 10px 12px 0;'>{self.options.selected_investor_name}</div>",
                       unsafe_allow_html=True, )

        fy = utils.current_fy()
        today = date.today()
        as_on_date = st.slider(label="As On Date",
                               min_value=today,
                               max_value=today + timedelta(days=365*2),
                               value=today,
                               step=timedelta(days=1),
                               format="[As on ]D-MMM-YY",
                               label_visibility="collapsed",
                               )

        as_on_date_str = as_on_date.strftime("%d-%b-%Y")
        self.as_on_date = as_on_date

        if "pin-metrics" not in st.session_state:
            st.session_state["pin-metrics"] = False
        with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="top"):
            # metrics_box = st.expander("Summary Metrics", expanded=True) if st.session_state["pin-metrics"] else st.popover(f"Summary Metrics", width=200)
            with st.container(horizontal=True, vertical_alignment="center"):
                if st.session_state["pin-metrics"]:
                    metrics_box = st.container()
                    with metrics_box.container(horizontal=True, vertical_alignment="center", ):
                        st.button("Summary Metrics  ", width=200, disabled=True)
                        st.toggle("Sticky metrics window...", key="pin-metrics")
                else:
                    metrics_box = st.popover(f"Summary Metrics", width=200)
                    st.toggle("Sticky metrics window...", key="pin-metrics")

            if st.button("Change account", type="secondary"):
                user_options.user_options(select_investor=True,)

        # Compile data - used for main dataframe and for summary metrics
        sequence = [i+1 for i in range(len(self.investments))]
        investment_column = [f"{investment.scheme_name} /{investment.folio}" for investment in self.investments]
        investment_tax_type_column = [investment.tax_treatment for investment in self.investments]
        sold_value_fy = [sum([txn.sell_amount for txn in investment.matched_txns
                             if txn.fy == fy]) for investment in self.investments]
        sold_for_asr = [sum([txn.sell_amount for txn in investment.matched_txns
                             if txn.fy == fy and
                             (txn.is_taxable_at_slab_rate if self.tax_type == "ASR" else txn.is_taxable_at_stcg)])
                            for investment in self.investments]
        real_asr = [sum([txn.pnl for txn in investment.matched_txns
                             if txn.fy == fy and
                             (txn.is_taxable_at_slab_rate if self.tax_type=="ASR" else txn.is_taxable_at_stcg)])
                             for investment in self.investments]
        sold_for_ltcg = [sum([txn.sell_amount for txn in investment.matched_txns
                            if txn.fy == fy and txn.is_taxable_at_ltcg]) for investment in self.investments]
        real_ltcg = [sum([txn.pnl for txn in investment.matched_txns
                            if txn.fy == fy and txn.is_taxable_at_ltcg]) for investment in self.investments]
        current_value = [investment.value for investment in self.investments]
        asr_sellable_value = [sum([txn.unsold_value for txn in investment.buy_txns
                             if txn.load_free_from_date < as_on_date < txn.ltcg_from_date]) for investment in self.investments]
        asr_sellable_units = [sum([txn.unsold_units for txn in investment.buy_txns
                             if txn.load_free_from_date < as_on_date < txn.ltcg_from_date]) for investment in self.investments]
        asr_unreal_gain = [sum([txn.unrealized_pnl for txn in investment.buy_txns
                             if txn.load_free_from_date < as_on_date < txn.ltcg_from_date]) for investment in self.investments]
        ltcg_sellable_value = [sum([txn.unsold_value for txn in investment.buy_txns
                             if as_on_date >= txn.ltcg_from_date]) for investment in self.investments]
        ltcg_sellable_units = [sum([txn.unsold_units for txn in investment.buy_txns
                             if as_on_date >= txn.ltcg_from_date]) for investment in self.investments]
        ltcg_unreal_gain = [sum([txn.unrealized_pnl for txn in investment.buy_txns
                             if as_on_date >= txn.ltcg_from_date]) for investment in self.investments]

        # if st.session_state["pin-metrics"]:
        #     with metrics_box.container(horizontal=True, vertical_alignment="center",):
        #         st.button("Summary Metrics  ˄", width=200,disabled=True)
        #         st.toggle("Sticky metrics window...", key="pin-metrics")
        col1, col2, col3, col4, col5 = metrics_box.container(border=st.session_state["pin-metrics"], width=800).columns(5, width=800)
        # Current Value     Sellable for ASR/STCG    Unrealized ASR/STCG      Sellable for LTCG   Unrealized LTCG
        col1.metric("Current Value", value=utils.number_str(sum(current_value), 2, compact="L"),
                    help=f"Total value of current holdings (all FY): ₹{utils.number_str(sum(current_value))}")
        col2.metric(f"Sellable for {self.tax_type}", value=utils.number_str(sum(asr_sellable_value), 2, compact="L"),
                    help=f"Value of units that would give {self.tax_type} Gains if sold on selected date {as_on_date_str}: ₹{utils.number_str(sum(asr_sellable_value))}")
        col3.metric(f"Unrealized {self.tax_type}", value=utils.number_str(sum(asr_unreal_gain), 2, compact="L"),
                    help=f"Unrealized {self.tax_type} Gains as on selected date {as_on_date_str}: ₹{utils.number_str(sum(asr_unreal_gain))}")
        col4.metric("Sellable for LTCG", value=utils.number_str(sum(ltcg_sellable_value), 2, compact="L"),
                    help=f"Value of units that will give LTCG Gains if sold on selected date {as_on_date_str}: ₹{utils.number_str(sum(ltcg_sellable_value))}")
        col5.metric("Unrealized LTCG", value=utils.number_str(sum(ltcg_unreal_gain), 2, compact="L"),
                    help=f"Unrealized LTCG Gains as on selected date {as_on_date_str}: ₹{utils.number_str(sum(ltcg_unreal_gain))}")
        # Sold Value        Sold for ASr        Realized ASR/STCG        Sold for LTCG       Realized LTCG
        col1.metric("Sold Value", value=utils.number_str(sum(sold_value_fy), 2, compact="L"),
                    help=f"Total value of sold units in current FY {fy}: ₹{utils.number_str(sum(sold_value_fy))}")
        col2.metric(f"Sold for {self.tax_type}", value=utils.number_str(sum(sold_for_asr), 2, compact="L"),
                    help=f"Sold value of units that gave {self.tax_type} Gains in the FY {fy}: ₹{utils.number_str(sold_for_asr)}")
        col3.metric(f"Realized {self.tax_type}", value=utils.number_str(sum(real_asr), 2, compact="L"),
                    help=f"Realized {self.tax_type} Gains in the FY {fy}: ₹{utils.number_str(real_asr)}")
        col4.metric("Sold for LTCG", value=utils.number_str(sum(sold_for_ltcg), 2, compact="L"),
                    help=f"Sold value of units that gave LTCG Gains in the FY {fy}: ₹{utils.number_str(sold_for_ltcg)}")
        col5.metric("Realized LTCG", value=utils.number_str(sum(real_ltcg), 2, compact="L"),
                    help=f"Realized LTCG Gains in the FY {fy}: ₹{utils.number_str(real_ltcg)}")

        df1 = pd.DataFrame({
            "sequence": sequence,
            "investment": investment_column,
            "tax_type": investment_tax_type_column,
            "real_gain": real_asr,
            "real_ltcg":  real_ltcg,
            "current_value": current_value,
            "sellable_value": asr_sellable_value,
            "sellable_units": asr_sellable_units,
            "asr_unreal_gain": asr_unreal_gain,
            "ltcg_sell_value": ltcg_sellable_value,
            "ltcg_sellable_units": ltcg_sellable_units,
            "ltcg_unreal_gain": ltcg_unreal_gain,
        })
        df1.set_index(["sequence", "investment"], inplace=True)
        formatted_df1 = (df1.style.format(utils.number_str)
                         .format(lambda x: utils.number_str(x, 3), subset=["sellable_units", "ltcg_sellable_units"]))
        column_config_df1 = {
            "sequence": st.column_config.Column(label="#", help="Sequence #", width=24,),
            "investment": st.column_config.Column(
                label=f"Investments ({len(df1)})", width=350,
                help=f"Investments with realized or unrealized gains in FY {fy}",
            ),
            "tax_type": st.column_config.Column(
                label="MF Category", width="small", help="Taxation Catagoty of the MF Scheme Debt/Equity/Other"
            ),
            "amount_sold": st.column_config.Column(
                label="Amount sold", width="small", help="Value of units sold in current FY"
            ),
            "real_gain": st.column_config.Column(
                label=f"Realized {self.tax_type}", width="small", help=f"Realized {self.tax_type} Gains in current FY"
            ),
            "real_ltcg": st.column_config.Column(
                label="Realized LTCG", width="small", help="Realized LTCG Gains in current FY"
            ),
            "current_value": st.column_config.Column(
                label="Current Value", width="small", help="Total value of holdings"
            ),
            "sellable_value": st.column_config.Column(
                label=f"Sellable Value @{self.tax_type}", width="small",
                help=f"Value of units that are load free and not crossed LTCG date (for {self.tax_type} Gains) as on {as_on_date_str}"
            ),
            "sellable_units": st.column_config.Column(
                label=f"Sellable Units ({self.tax_type})", width="small",
                help=f"Value of units that are load free and not crossed LTCG date (for {self.tax_type} Gains) as on {as_on_date_str}"
            ),
            "asr_unreal_gain": st.column_config.Column(
                label=f"Unrealized {self.tax_type}", width="small", help=f"Unrealized {self.tax_type} gain as on {as_on_date_str}"
            ),
            "ltcg_sell_value": st.column_config.Column(
                label="Value @LTCG", width="small",
                help=f"Value of units that have crossed LTCG date (for LTCG Gains) as on {as_on_date_str}"
            ),
            "ltcg_sellable_units": st.column_config.Column(
                label=f"LTCG Sellable Units ({self.tax_type})", width="small",
                help=f"Value of units that have/would crossed LTCG date (for {self.tax_type} Gains) as on {as_on_date_str}"
            ),
            "ltcg_unreal_gain": st.column_config.Column(
                label="Unrealized LTCG", width="small", help=f"Unrealized LTCG gain as on {as_on_date_str}"
            ),
        }

        # df_space = st.empty()
        dss_df_event = st.dataframe(formatted_df1,
                     column_config=column_config_df1,
                     selection_mode=["single-row"],
                     on_select="rerun" if st.session_state.get("select_investment") else 'ignore',
                     key="dss_df_event"
                     )
        try:
            selected_rows = dss_df_event["selection"]["rows"]
            self.selected_investment = self.investments[selected_rows[0]]
        except Exception as e:
            selected_rows = []
        st.toggle("Select investment for transaction level details", key="select_investment")

        # if not selected_rows and st.session_state.get("select_investment"):
        #     st.caption("Select an investment for transaction level details")
        #
        return self

class DssTxns:
    def __init__(self, investment, as_on_date, tax_type):
        self.investment = investment
        self.fy = utils.current_fy()
        self.tax_type = tax_type
        # self.fy = fy
        self.as_on_date = as_on_date

    def show(self):
        # col1, col2 = st.columns(2)
        st.caption(f"<div style='text-align: left; font-size: 1rem'>"
                   f"{self.investment.scheme_name} /{self.investment.folio} ({self.investment.tax_treatment})"
                   f"</div>",
                   unsafe_allow_html=True,
                   )
        unsold, sold = st.tabs(["Unrealized Gains", "Realized Gains"])
        # Realized Gains
        # Sold Units (matched Txns) during the Financial Year
        # Sale Date | Sale Value | Sale Price | Units | Buy Date | Buy Value | Buy Price | ASR/STCG Gain | LTCG | CAGR $
        txns = [txn for txn in self.investment.matched_txns if txn.fy == self.fy]
        df1 = pd.DataFrame({
            "sequence": [i + 1 for i in range(len(txns))],
            "sale_date": [txn.sell_date for txn in txns],
            "sale_price": [txn.sell_txn.price for txn in txns],
            "sale_value": [txn.sell_amount for txn in txns],
            "units": [txn.units for txn in txns],
            "buy_date": [txn.buy_date for txn in txns],
            "buy_price": [txn.buy_txn.price for txn in txns],
            "buy_value": [txn.buy_amount for txn in txns],
            "asr_gain": [(txn.pnl if
                        (txn.is_taxable_at_slab_rate if self.tax_type == "ASR" else txn.is_taxable_at_stcg)
                        else 0) for txn in txns],
            "ltcg": [(txn.pnl if txn.is_taxable_at_ltcg else 0) for txn in txns],
            "gain%": [(txn.pnl / txn.buy_amount * 100) for txn in txns],
        })
        df1.set_index(["sequence"], inplace=True)
        formatted_df1 = (df1.style.format(
                lambda x: utils.number_str(x, 4), subset=["sale_price", "buy_price", "units"],
            ).format(
                lambda x: utils.number_str(x, ), subset=["sale_value", "buy_value", "asr_gain", "ltcg"],
            ).format(
            lambda x: utils.number_str(x, 1, suffix="%"), subset=["gain%"],
            )
        )
        column_config_df1 = {
            "sequence": st.column_config.Column(label="#", help="Sequence #", width=24, ),
            "sale_date": st.column_config.DateColumn(label="Sale Date", format="DD-MMM-YYYY", width=90),
            "sale_price": st.column_config.Column(label="Sale Price", width="small", help="Sale NAV"),
            "sale_value": st.column_config.Column(label="Sale Value", width="small", help="Sale Value of matched units"),
            "units": st.column_config.Column(label="Units", width="small", help="Matched Units"),
            "buy_date": st.column_config.DateColumn(label="Buy Date", format="DD-MMM-YYYY", width=90),
            "buy_price": st.column_config.Column(label="Buy Price", width="small", help="Purchase NAV"),
            "buy_value": st.column_config.Column(label="Cost", width="small", help="Cost of matched units"),
            "asr_gain": st.column_config.Column(label=f"{self.tax_type} Gain", width="small", help="Gain taxable at Applicable Slab Rate"),
            "ltcg": st.column_config.Column(label="LTCG", width="small", help="Gain taxable as LTCG"),

            "gain%": st.column_config.Column(label="Gain %", width="small", help="Absolute Gain %"),
        }

        with sold:
            st.caption(f"<div style='text-align: right;'>"
                         f"Sold units in FY {self.fy}"
                         f"</div>",
                         unsafe_allow_html=True,
                         )
            st.dataframe(formatted_df1, column_config=column_config_df1)

        # Unrealized Gains => Unsold units (buy txns)
        # Buy Date | Units | Buy Price | Total Cost | Load Free Date | LTCG Start Date | PnL @ Current NAV | CAGR @ NAV Date
        txns = [txn for txn in self.investment.buy_txns if txn.unsold_units > 0]
        df2 = pd.DataFrame({
            "sequence": [i+1 for i in range(len(txns))],
            "buy_date": [txn.txn_date for txn in txns],
            "units": [txn.unsold_units for txn in txns],
            "buy_price": [txn.price for txn in txns],
            "cost": [txn.unsold_amount for txn in txns],
            "is_load_free": [("Yes" if txn.load_free_from_date < self.as_on_date else "No") for txn in txns],
            "is_ltcg": ["Yes" if txn.ltcg_from_date <= self.as_on_date else "No" for txn in txns],
            "load_free_date": [txn.load_free_from_date for txn in txns],
            # "ltcg_start_date": [txn.ltcg_from_date for txn in txns]
            #                     if self.investment.tax_treatment.lower() != "debt" else ([None] * len(txns)),
            "ltcg_start_date": [txn.ltcg_from_date for txn in txns]
                                if self.investment.is_under_ltcg else ([None] * len(txns)),
            "unsold_value": [txn.unsold_value for txn in txns],
            "pnl": [txn.unrealized_pnl for txn in txns],
            # "gain%": [txn.unrealized_cagr for txn in txns],
            "gain%": [(txn.unrealized_pnl / txn.unsold_amount) for txn in txns],
        })
        # df2["ltcg_start_date"] = pd.to_datetime(df2["ltcg_start_date"], errors="coerce")
        # df2["ltcg_start_date"] = df2["ltcg_start_date"].dt.strftime("%d-%b-%Y").fillna("x")

        df2.set_index(["sequence"], inplace=True)
        formatted_df2 = (df2.style.format({
            "units": lambda x: utils.number_str(x, 4),
            "buy_price": lambda x: utils.number_str(x, 4),
            "cost": lambda x: utils.number_str(x, ),
            "unsold_value": lambda x: utils.number_str(x, ),
            "pnl": lambda x: utils.number_str(x,),
            "gain%": lambda x: utils.number_str(x*100, 1, suffix="%"),
            })
        )
        column_config_df2 = {
            "sequence": st.column_config.Column(label="#", help="Sequence #", width=24, ),
            "buy_date": st.column_config.DateColumn(label="Buy Date", format="DD-MMM-YYYY", width=90),
            "units": st.column_config.Column(label="Units", width="small", help="Bought Units"),
            "buy_price": st.column_config.Column(label="Buy Price", width="small", help="Purchase NAV"),
            "cost": st.column_config.Column(label="Total Cost", width="small", help="Cost of unsold units"),
            "is_load_free": st.column_config.Column(label="Load Free?", width="small",
                                                    help="Is this buy transaction load free as on the selected date?"),
            "is_ltcg": st.column_config.Column(label="LTCG?", width="small",
                                               help="gas this PnL become LTCG as on the selected date?"),
            "load_free_date": st.column_config.DateColumn(label="Load Free Date", format="DD-MMM-YYYY", width=90),
            "ltcg_start_date": st.column_config.DateColumn(label="LTCG Start Date", format="DD-MMM-YYYY", width=90),
            "unsold_value": st.column_config.Column(label="Unsold Value", width="small", help="Value of unsold units"),
            "pnl": st.column_config.Column(label="P&L", width="small", help="Profit / Loss"),
            "gain%": st.column_config.Column(label="Gain %", width="small", help="Absolute Gain %"),
        }

        with unsold:
            st.caption(f"<div style='text-align: right;'>"
                         f"Unsold units as on {self.as_on_date.strftime('%b %d, %Y')} (NAV {self.investment.nav} @ {self.investment.nav_date.strftime('%d-%b-%Y')})"
                         f"</div>",
                         unsafe_allow_html=True,
                         )
            dss_df_event = st.dataframe(formatted_df2, column_config=column_config_df2,)
        return self


def dss(tax_type):
    report = RedemptionsDSS(tax_type)
    report.show()
    if report.selected_investment is not None:
        txns_details = DssTxns(report.selected_investment, report.as_on_date, tax_type)
        txns_details.show()

def income_dss():
    dss("ASR")

def stcg_dss():
    dss("STCG")

