import streamlit as st
import pandas as pd

import utils.utils as utils
import view.options as user_options

class Investments:
    def __init__(self,):
        self.options = st.session_state.options  # Options object
        self.investors = [st.session_state.user.investors[name] for name in self.options.selected_investors_names]
        self.investments = [investment for investor in self.investors
                            for investment in investor.investments
                            if investment.filter(
                                    self.options.selected_hide_before_date,
                                    self.options.selected_cats,
                                    self.options.selected_subs
                            )
                            ]
        self.investments.sort(key=lambda investment: investment.scheme_name)
        self.df1 = None
        self.df2 = None
        self.formatted_df1 = None
        self.formatted_df2 = None
        self.column_config_df1 = None
        self.column_config_df2 = None
        self.selected_rows = None
        self.metrics_cols = None

    def prepare_df1(self):
        self.df1 = pd.DataFrame({})

        values = [((i.nav * i.holding) if i.nav is not None else 0) for i in self.investments]
        # self.df1["Tax Treatment"] = [i.tax_treatment for i in self.investments]
        # self.df1["Category"] = [i.mf_category for i in self.investments]
        self.df1["value"] = values
        total_value = sum(values)
        percents = [v/total_value for v in values]
        self.df1["%"] = percents
        units = [i.holding for i in self.investments]
        self.df1["units"] = units
        NAVs = [i.nav for i in self.investments]
        self.df1["nav"] = NAVs
        nav_dates = [i.nav_date for i in self.investments]
        self.df1["nav_date"] = nav_dates
        last_buy_dates = [i.buy_txns[-1].txn_date for i in self.investments]
        self.df1["last_buy_date"] = last_buy_dates
        last_sell_dates = [(i.sell_txns[-1].txn_date if len(i.sell_txns) > 0 else None) for i in self.investments]
        self.df1["last_sell_date"] = last_sell_dates
        self.df1["last_sell_date"] = pd.to_datetime(self.df1["last_sell_date"], errors="coerce")
        self.df1["last_sell_date"] = self.df1["last_sell_date"].dt.strftime("%d-%b-%Y").fillna("x")

        if len(self.investors) > 1:
            self.df1.insert(0, "Investor", [i.investor.name.split()[0] for i in self.investments])

        self.df1["Investments"] = [f"{i.scheme_name} /{i.folio}" for i in self.investments]
        self.df1.set_index(["Investments"], inplace=True)
        # self.df1.sort_index(inplace=True)

        # Last buy date is always expected but last sell date may be None if never sold
        self.last_txn_date = max(last_buy_dates + [d for d in last_sell_dates if d is not None]) if self.investments else None
        return self

    def format_df1(self):
        self.formatted_df1 = self.df1.style.format({
            "value": lambda x: utils.number_str(x),
            "%": lambda x: utils.number_str(x*100, 1) + ("%" if float(x) > 0 else ""),
            "units": lambda x: utils.number_str(x),
            "nav": lambda x: utils.number_str(x, 2),
            # "last_sell_date": lambda x: x if x is not None else "__",
            # "last_sell_date": lambda x: "__" if pd.isna(x) else x,
        })
        self.column_config_df1 = {
            "value": st.column_config.Column(
                label="Value",
                width="small",
            ),
            "Investments": st.column_config.Column(
                label=f"Investments ({len(self.investments)})",
                # width="large",
                width=350,
            ),

            "%": st.column_config.Column(label="%", width=50),
            "units": st.column_config.Column(label="Units"),
            "nav": st.column_config.Column(label="NAV"),
            "nav_date": st.column_config.DateColumn(
                label="NAV Date",
                format="DD-MMM-YYYY",
            ),
            "last_buy_date": st.column_config.DateColumn(
                label="Last Buy Date",
                format="DD-MMM-YYYY",
            ),
            "last_sell_date": st.column_config.Column(
                label="Last Sell Date",
                # format="DD-MMM-YYYY",
            )
        }
        # self.formatted_df = self.df
        return self

    def show_df1(self):
        # Show Header Data
        with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="bottom"):
            with st.container():
                st.write(f"#### Holding Details")
                metrics_box = st.popover(f"Summary Metrics", width=200)
            with st.container(horizontal_alignment="right"):
                with st.container(horizontal_alignment="right", horizontal=True):
                    names = ", ".join(investor.name for investor in self.investors)
                    # for investor in self.investors:
                    st.caption(f"<div style='text-align: right; font-size: 1rem; color:#279FF5; font-weight:600; "
                               f"margin:-12px 10px 12px 0;'>{names}</div>",
                               unsafe_allow_html=True, )
                if st.button("Modity filters...", type="secondary") or not self.options.selected_investors_names:
                    user_options.user_options(True, True, True)

        with metrics_box:
            st.metric(label=f"Total Value ₹ ({len(self.investments)} investment{"s" if len(self.investments) > 1 else ""})",
                           value=utils.number_str(sum(self.df1["value"]), 2, compact="L"),
                           border=False,
                           help="₹"+utils.number_str(sum(self.df1["value"]),))

        main_df_event = st.dataframe(self.formatted_df1,
                                     selection_mode="multi-row",
                                     # on_select=self.select_rows,
                                     on_select="rerun", #if st.session_state.drill_down_flag else "ignore",
                                     key="main_df_event",
                                     column_config=self.column_config_df1,
                                     )

        # self.selected_rows = st.session_state.main_df_event["selection"]["rows"]
        try:    # In case when on_select is "ignore", main_df_event is not subscriptable
            self.selected_rows = main_df_event["selection"]["rows"]
        except Exception:
            self.selected_rows = []

        if len(self.df1) > 0:
            with st.container(horizontal=True, horizontal_alignment="distribute"):
                if len(self.options.selected_cats) > 0 or len(self.options.selected_subs) > 0:
                    st.text("Filtered on categories:")
                    for cat in self.options.selected_cats:
                        st.badge(cat)
                    for cat, subs in self.options.selected_subs.items():
                        for sub in subs:
                            st.badge(f"{cat}/{sub}", color="yellow")
                # if not self.selected_rows:
                #     st.caption(f"<div style='text-align: left; font-weight: 500; '>"
                #                  f"Select from the above investments for transaction details"
                #                  f"</div>",
                #                  unsafe_allow_html=True,
                #                  )
                if self.last_txn_date is not None:
                    st.caption(f"<div style='text-align: right; font-weight: 500; margin-top: -20px;'>"
                                 f"Last transaction date: {self.last_txn_date.strftime('%d-%b-%Y')}"
                                 f"</div>",
                                 unsafe_allow_html=True,
                                 )


        hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}   /* Hide hamburger menu */
            footer {visibility: hidden;}      /* Hide footer */
            </style>
        """
        # st.markdown(hide_streamlit_style, unsafe_allow_html=True)
            # header {visibility: hidden;}      /* Hide top header (optional) */

        reduce_header = """
            <style>
            /* Reduce top header height */
            header[data-testid="stHeader"] {
                height: 60px;        /* adjust as needed */
                background: white;   /* keep background clean */
            }
            /* Push content up to remove the gap */
            div.block-container {
                padding-top: 2rem;   /* reduce padding from default ~6rem */
            }
            </style>
        """
        # st.markdown(reduce_header, unsafe_allow_html=True)

        # if st.button("User options...", type="tertiary"):
        #     user_options.user_options(True, True, True)

        return self

    def prepare_df2(self):
        txn_dates = []
        buy_sell = []
        units = []
        prices = []
        amounts = []
        taxes = []
        balance_units = []
        schemes = []
        self.selected_investments_value = 0

        for i in self.selected_rows:
            investment = self.investments[i]
            # st.write(investment.scheme_name)
            # Prepare relevant data for current investment
            txn_dates += [txn.txn_date for txn in investment.txns]
            # buy_sell += [("Buy" if txn.units > 0 else "Sell") for txn in investment.txns]
            buy_sell += [txn.type for txn in investment.txns]
            units += [abs(txn.units) for txn in investment.txns]
            prices += [txn.price for txn in investment.txns]
            amounts += [abs(txn.units * txn.price)+(txn.tax if txn.type=="buy" else -txn.tax) for txn in investment.txns]
            taxes += [txn.tax for txn in investment.txns]
            balance_units += [txn.cumm_balance for txn in investment.txns]

            schemes += [f'{investment.scheme_name} /{str(investment.folio)}'] * len(investment.txns)
            self.selected_investments_value += investment.value

        self.df2 = pd.DataFrame({
            "investments": schemes,
            "txn_date": txn_dates,
            "buy_sell": buy_sell,
            "amount": amounts,
            "units": units,
            "price": prices,
            "tax": taxes,
            "balance_units": balance_units,
        })
        self.df2.set_index(["investments"], inplace=True)

        return self

    def format_df2(self):
        self.formatted_df2 = self.df2.style.format({
            "amount": lambda x: utils.number_str(x),
            "units": lambda x: utils.number_str(x, 2),
            "balance_units": lambda x: utils.number_str(x, 2),
            "price": lambda x: utils.number_str(x, 2),
            "tax": lambda x: utils.number_str(x, 2),
        })
        self.column_config_df2 = {
            "investments": st.column_config.Column(label=f"Investments ({len(self.selected_rows)})"),  # width="large", width=350,),
            "txn_date": st.column_config.DateColumn(label="Txn Date", format="DD-MMM-YYYY",),
            "buy_sell": st.column_config.Column(label="Buy/Sell"),
            "amount": st.column_config.Column(label="Amount ₹", help="Units*Price + Tax"),
            "units": st.column_config.Column(label="Units"),
            "price": st.column_config.Column(label="Price"),
            "tax": st.column_config.Column(label="Tax"),
            "balance_units": st.column_config.Column(label="Balance"),
        }
        return self

    def show_report2(self):
        st.write("##### Transaction details of selected investments")
        st.metric(f"Selected ₹ ({len(self.selected_rows)} investment{'s' if len(self.selected_rows) > 1 else ''})",
                       value=utils.number_str(self.selected_investments_value,2, compact="L"),
                       help ="₹" + utils.number_str(self.selected_investments_value,),
                       border=False,)

        # col1, col2 = st.columns(2)
        # col1.caption(f"<div style='text-align: left;'>"
        #              f"Selected {len(self.selected_rows)} of {len(self.investments)} investments"
        #              f"</div>",
        #              unsafe_allow_html=True,
        #             )

        st.dataframe(self.formatted_df2, column_config=self.column_config_df2)

        col1, col2 = st.columns(2)

        col1.caption(f"<div style='margin-top: -18px'>"
                     f"First transaction date: {min(self.df2['txn_date']).strftime('%d-%b-%Y')}"
                     f"</span>",
                     unsafe_allow_html=True,
                     )
        col2.caption(f"<div style='text-align: right; font-weight: 500; margin-top: -18px'>"
                     f"Last transaction date: {max(self.df2['txn_date']).strftime('%d-%b-%Y')}"
                     f"</span>",
                     unsafe_allow_html=True,
                     )



        # cols = self.sec_report_metrics.columns(2)
        # Do not delete - To display text at the bottom of a box (ChatGpt solution)
        # cols[1].html(f""" <div style=" height: 60px; display: flex; align-items: flex-end;
        #         justify-content: flex-end;
        #         font-weight: 500;">
        #         {self.investor.name}
        #     </div>
        #     """)

        return self

# with st.sidebar:
#     filters.choose_investors()
#     filters.zero_balance_option()
#     filters.show_tags()
#     st.empty()
#
report = Investments()
(
    report
    .prepare_df1()
    .format_df1()
    .show_df1()
 )
if len(report.selected_rows) > 0:
    (report
     .prepare_df2()
     .format_df2()
     .show_report2()
     )
