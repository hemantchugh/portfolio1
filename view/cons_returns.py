import streamlit as st
import pandas as pd

import utils.utils as utils
from model.xirr import xirr
import view.options as user_options

class Returns:
    def __init__(self):
        self.options = st.session_state.options
        self.investors = [st.session_state.user.investors[name] for name in self.options.selected_investors_names]
        self.investments = [investment for investor in self.investors
                            for investment in investor.investments
                            if investment.filter(
                                    self.options.selected_hide_before_date,
                                    self.options.selected_cats,
                                    self.options.selected_subs)
                            ]
        self.investments.sort(key=lambda investment: investment.scheme_name)

        self.df1, self.df2, self.df3 = None, None, None
        self.formatted_df1 = None
        self.formatted_df2 = None
        self.formatted_df3 = None
        self.column_config_df1 = None
        self.column_config_df2 = None
        self.column_config_df3 = None
        self.selected_rows = None
        self.selected_columns = None

    def prepare_df1(self):
        self.df1 = pd.DataFrame({})
        values = [((i.nav * i.holding) if i.nav is not None else 0) for i in self.investments]
        realized_returns = [i.get_realized_pnl() for i in self.investments]
        realized_xirr = [i.realized_xirr() for i in self.investments]
        unrealized_returns = [i.get_unrealized_pnl() for i in self.investments]
        unrealized_xirr = [i.unrealized_xirr() for i in self.investments]
        # investor_name = [i.investor.name.split()[0] for i in self.investments]
        taxes = [i.total_taxes_paid for i in self.investments]
        total_returns = [r+u for r, u, t in zip(realized_returns, unrealized_returns, taxes)]
        total_irr = [i.total_xirr() for i in self.investments]

        self.df1 = pd.DataFrame({
            # "name": investor_name,
            "values": values,
            "total_returns": total_returns,
            "total_xirr": total_irr,
            "realized_returns": realized_returns,
            "realized_xirr": realized_xirr,
            "unrealized_returns": unrealized_returns,
            "unrealized_xirr": unrealized_xirr,
        })
        if len(self.investors) > 1:
            self.df1.insert(0, "Investor", [i.investor.name.split()[0] for i in self.investments])
        self.df1["investments"] = [f"{i.scheme_name} /{i.folio}" for i in self.investments]
        self.df1.set_index(["investments"], inplace=True)
        # self.df1.sort_index(inplace=True)
        return self

    def format_df1(self):
        self.formatted_df1 = self.df1.style.format(
            utils.number_str,
            subset = ["values", "realized_returns", "unrealized_returns", "total_returns"],
        ).format(
            lambda i: utils.number_str(i*100, 1, suffix="%"), #+("" if float(i) == 0 else "%"),
            subset = ["realized_xirr", "unrealized_xirr", "total_xirr"],
        )

        self.column_config_df1 = {
            "investor": st.column_config.Column(label="Investor", width="small",),
            "values": st.column_config.Column(label="Market Value", width="small",),
            "realized_returns": st.column_config.Column(label="Real'd Returns", width="small",),
            "unrealized_returns": st.column_config.Column(label="Unreal'd Returns", width="small",),
            "total_returns": st.column_config.Column(label="Total Returns", width="small",),
            "realized_xirr": st.column_config.Column(label="Real'ed XIRR", width="small",),
            "unrealized_xirr": st.column_config.Column(label="Unreal'd XIRR", width="small",),
            "total_xirr": st.column_config.Column(label="Total XIRR", width="small",),
            "investments": st.column_config.Column(label=f"Investments ({len(self.investments)})", help="Scheme Name and Folio", width=350,),
        }
        return self

    def show_df1(self):
        # Show Header Data
        with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="bottom"):
            with st.container():
                st.write(f"#### Consolidated Returns")
                metrics_box = st.popover(f"Summary Metrics", width=200)
            with st.container(horizontal_alignment="right"):
                with st.container(horizontal_alignment="right", horizontal=True):
                    names = ", ".join(investor.name for investor in self.investors)
                    # for investor in self.investors:
                    st.caption(f"<div style='text-align: right; font-size: 1rem; color:#279FF5; font-weight:600; "
                               f"margin:-12px 10px 12px 0;'>{names}</div>",
                               unsafe_allow_html=True, )
                if st.button("Modity filters...", type="secondary"):
                    # user_options.user_options(True, True, True,)
                    user_options.user_options(select_investors=True, select_zero_balance_options=True,
                                              select_categories=True)

        # with metrics_box:
        col1, col2, col3, col4 = metrics_box.columns(4, gap="small", width=800)
        with col1:
            st.metric(label="Holdings Value",
                           value=utils.number_str(sum(self.df1["values"]), 2, compact="L"),
                           help="Market value of investments in the below table: ₹"+utils.number_str(sum(self.df1["values"]),))
            st.metric(label="Investments #",
                           value=utils.number_str(len(self.investments)),
                           help="Number of investments in the below table",)
        with col2:
            st.metric(label="Total Returns",
                           value=utils.number_str(sum(self.df1["total_returns"]), 2, compact="L"),
                           help="Total Returns (Realized + Unrealized) on below investments: ₹"+utils.number_str(sum(self.df1["total_returns"]),))
            st.metric(label="Total XIRR",
                           value=utils.number_str(xirr(self.investments)*100, 1, suffix="%"),
                           help="Rate of return on below investments",)
        with col3:
            # col3, col4 = st.columns(2)
            st.metric(label="Realized ₹",
                           value=utils.number_str(sum(self.df1["realized_returns"]), 2, compact="L"),
                           help="Realized returns on below investments: ₹"+utils.number_str(sum(self.df1["realized_returns"]),))
            st.metric(label="Realized XIRR",
                           value=utils.number_str(xirr(self.investments, realized=True)*100, 1, suffix="%"),
                           help="Rate of return (Realized) on below investments",)
        with col4:
            st.metric(label="Unrealized ₹",
                           value=utils.number_str(sum(self.df1["unrealized_returns"]), 2, compact="L"),
                           help="Unrealized returns on below investments: ₹"+utils.number_str(sum(self.df1["unrealized_returns"]),))
            st.metric(label="Unrealized XIRR",
                           value=utils.number_str(xirr(self.investments, unrealized=True,)*100, 1, suffix="%"),
                           help="Rate of return (Unrealized) on below investments",)

        main_df_event = st.dataframe(self.formatted_df1,
                                     selection_mode=["single-row"],
                                     on_select="rerun",  # if st.session_state.drill_down_flag else "ignore",
                                     # key="main_df_event",
                                     column_config=self.column_config_df1,
                                     # column_order=("name", "values", "total_xirr",
                                     #               "realized_returns", "realized_xirr",
                                     #               "unrealized_returns", "unrealized_xirr"),
                                     )

        try:    # In case when on_select is "ignore", main_df_event is not subscriptable
            self.selected_rows = main_df_event["selection"]["rows"]
            # st.write(main_df_event)
        except Exception:
            self.selected_rows = []

        if len(self.df1) > 0:
            with st.container(horizontal=True, horizontal_alignment="left"):
                if len(self.options.selected_cats) > 0 or len(self.options.selected_subs) > 0:
                    st.text("Filtered on categories:")
                    for cat in self.options.selected_cats:
                        st.badge(cat)
                    for cat, subs in self.options.selected_subs.items():
                        for sub in subs:
                            st.badge(f"{cat}/{sub}", color="yellow")

        return self

    def prepare_report2(self):
        # Realized Returns Txn Level Report (Matched units of matched Txns)
        investment = self.investments[self.selected_rows[0]]
        txns = investment.matched_txns
        self.df2 = pd.DataFrame({
            "sell_date" : [txn.sell_txn.txn_date for txn in txns],
            "sell_price": [txn.sell_txn.price for txn in txns],
            "sell_amount": [txn.sell_amount for txn in txns],
            "buy_date"  : [txn.buy_txn.txn_date  for txn in txns],
            "buy_price" : [txn.buy_txn.price for txn in txns],
            "buy_amount": [txn.buy_amount for txn in txns],
            "units"     : [txn.units for txn in txns],
            "tax"       : [(txn.stamp_duty + txn.stt) for txn in txns],
            "return"    : [txn.pnl for txn in txns],
            "cagr"      : [txn.cagr for txn in txns],
        })
        self.df2.sort_values("sell_date", inplace=True, ascending=False)

        # Unrealized Returns Txn Level Report (Unsold units of Buy Txns)
        txns = [txn for txn in investment.buy_txns if txn.unsold_units > 0]
        self.df3 = pd.DataFrame({
            "buy_date"      : [txn.txn_date for txn in txns],
            "buy_price"     : [txn.price for txn in txns],
            "unsold_units"  : [txn.unsold_units for txn in txns],
            "buy_amount"    : [txn.unsold_amount for txn in txns],
            "value"         : [txn.unsold_units * investment.nav for txn in txns],
            "tax"           : [txn.stamp_duty * txn.unsold_units / txn.units for txn in txns],
            "return"        : [txn.unrealized_pnl for txn in txns],
            "cagr"          : [txn.unrealized_cagr for txn in txns],
        })

        return self

    def format_report2(self):
        self.formatted_df2 = self.df2.style.format({
            "sell_price": lambda x: utils.number_str(x, 2),
            "sell_amount": lambda x: utils.number_str(x,),
            "buy_price": lambda x: utils.number_str(x, 2),
            "buy_amount": lambda x: utils.number_str(x, ),
            "units": lambda x: utils.number_str(x, 2),
            "tax": lambda x: utils.number_str(x, 2),
            "return": lambda x: utils.number_str(x, ),
            "cagr": lambda x: utils.number_str(x*100, 1, suffix="%"),
        })
        self.column_config_df2 = {
            "sell_date": st.column_config.DateColumn(label="Sell Date", format="DD-MMM-YYYY", width=90,),
            "sell_price": st.column_config.Column(label="Sell Price", width="small",),
            "sell_amount": st.column_config.Column(label="Sell Amount", width="small",),
            "buy_date": st.column_config.DateColumn(label="Buy Date", format="DD-MMM-YYYY", width=90,),
            "buy_price": st.column_config.Column(label="Buy Price", width="small",),
            "buy_amount": st.column_config.Column(label="Buy Amount", width="small",),
            "units": st.column_config.Column(label="Units", width="small",),
            "tax": st.column_config.Column(label="Tax", width="small",),
            "return": st.column_config.Column(label="Return", width="small",),
            "cagr": st.column_config.Column(label="CAGR", width="small",),
        }

        self.formatted_df3 = self.df3.style.format({
            "buy_price": lambda x: utils.number_str(x, 2),
            "buy_amount": lambda x: utils.number_str(x,),
            "unsold_units": lambda x: utils.number_str(x, 2),
            "value": lambda x: utils.number_str(x, ),
            "tax": lambda x: utils.number_str(x, 2),
            "return": lambda x: utils.number_str(x, ),
            "cagr": lambda x: utils.number_str(x*100, 1, suffix="%"),
        })
        self.column_config_df3 = {
            "buy_date": st.column_config.DateColumn("Buy Date", format="DD-MMM-YYYY", width=90,),
            "buy_price": st.column_config.Column("Buy Price", width="small",),
            "unsold_units": st.column_config.Column("Unsold Units", width="small",),
            "buy_amount": st.column_config.Column("Amount", width="small",),
            "value": st.column_config.Column("Value", width="small",),
            "tax": st.column_config.Column("Stamp Duty", width="small",),
            "return": st.column_config.Column("Return", width="small",),
            "cagr": st.column_config.Column("CAGR", width="small",),
        }


        return self

    def show_report2(self):
        # col1, col2 = st.columns([3,1])
        investment = self.investments[self.selected_rows[0]]
        st.html(f"<div style='text-align: left; font-weight: 600; font-size: 1rem'>"
                     f"{investment.scheme_name} /{investment.folio}"
                     f"</span>",
                     # unsafe_allow_html=True,
                     )
        st.caption(f"<div style='text-align: left; font-weight: 600; font-size: 1rem'>"
                     f"Realized Returns"
                     f"</div>",
                     unsafe_allow_html=True,
                    )

        st.dataframe(self.formatted_df2, column_config=self.column_config_df2, hide_index=True)

        # col1, col2 = st.columns([1,2])
        st.caption(f"<div style='text-align: left; font-weight: 600; font-size: 1rem'>"
                     f"Unrealized Returns @ nav ₹{utils.number_str(investment.nav, 4)} "
                     f"on {investment.nav_date.strftime('%d-%b-%Y')}"
                     f"</div>",
                     unsafe_allow_html=True,
                    )
        st.dataframe(self.formatted_df3, column_config=self.column_config_df3, hide_index=True)

        # cols = self.sec_report_metrics.columns(2)
        # cols[1].metric(f"Selected ₹ ({len(self.selected_rows)} investment{'s' if len(self.selected_rows) > 1 else ''})",
        #                value=utils.number_str(sum(self.df2['value']),2, compact="L"), border=False)

        # Do not delete - To display text at the bottom of a box (ChatGpt solution)
        # cols[1].html(f""" <div style=" height: 60px; display: flex; align-items: flex-end;
        #         justify-content: flex-end;
        #         font-weight: 500;">
        #         {self.investor.name}
        #     </div>
        #     """)

        return self

report = Returns()
(
    report
    # .set_filter_criteria()
    # .filtered_investments()
    .prepare_df1()
    .format_df1()
    .show_df1()
 )
if len(report.selected_rows) > 0:
    (report
     .prepare_report2()
     .format_report2()
     .show_report2()
     )
