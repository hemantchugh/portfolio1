import streamlit as st
import pandas as pd

import utils.utils as utils
import view.options as user_options
from model.xirr import xirr

class Investments:
    TABLE_VIEW_TYPES = ["Holdings", "Returns", f"FY {utils.get_fy()}"]
    DF_COUNTER = 1
    def __init__(self,):
        self.options = st.session_state.options  # Options object
        self.investors = [st.session_state.user.investors[name] for name in self.options.selected_investors_names]
        self.investments = [investment for investor in self.investors
                            for investment in investor.investments
                            if investment.filter(
                                    self.options.selected_hide_before_date,
                                    # self.options.selected_cats,
                                    # self.options.selected_subs
                            )
                            ]
        self.value_total = sum(i.value for i in self.investments)
        self.investments.sort(key=lambda investment: investment.scheme_name)
        # self.table_view_type = None

    def show_page_headings(self):
        with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="top"):
            with st.container():
                st.write(f"#### Investments")
                value = sum(i.value for i in self.investments)
                label = (f"₹{utils.number_str(value, 2, compact="L")} ({len(self.investments)} "
                         f"MF scheme{"s" if len(self.investments) > 1 else ""})")
                st.metric(value="", label=label, help="₹" + utils.number_str(value))
            with st.container(horizontal_alignment="right"):
                with st.container(horizontal_alignment="right", horizontal=True):
                    names = ", ".join(investor.name for investor in self.investors)
                    st.caption(f"<div style='text-align: right; font-size: 1rem; color:#279FF5; font-weight:600; "
                               f"margin-bottom: 10px'>{names}</div>",
                               unsafe_allow_html=True, )
                if st.button("Modity filters...", type="secondary") or not self.options.selected_investors_names:
                    user_options.user_options(True, True,)
        return self

    def show_page_data(self):
        tab1, tab2, tab3 = st.tabs(["Unclassified", "Taxation classification", "Tags classification"])
        with tab1:
            self.tab_heading("All investments as per applied filters (if any)", key="tab1")
            self.tab_unclassified()
        with tab2:
            self.tab_heading("Investments classified as per provided taxation information", key="tab2")
            self.tab_taxation_classification()
        with tab3:
            self.tab_heading("Investments classified as per tags in Categoty/Sub-category format", key="tab3")
            self.tab_tags_classification()
        return self
    def tab_heading(self, caption="", key=""):
        def set_view_type():
            # Though there is different segment_control widget for each tab but they are all set to common value.
            st.session_state.table_view_type = st.session_state[key+"data_group_choice"]

        if "table_view_type" not in st.session_state:
            st.session_state.table_view_type = Investments.TABLE_VIEW_TYPES[0]
        with st.container(horizontal=True, horizontal_alignment="distribute", vertical_alignment="top"):
            st.caption(caption)
            # Data group choice selected within any tab shall be applied to every other tab
            st.session_state[key+"data_group_choice"] = st.session_state.table_view_type
            st.segmented_control(
                label="View", label_visibility="collapsed",
                options=Investments.TABLE_VIEW_TYPES,
                width=300, key=key+"data_group_choice",
                on_change=set_view_type
                )
        return self


    def tab_unclassified(self, ):
        # Show investments without any classification
        investments = self.investments
        self.show_data_block("All Schemes", investments, self.value_total, taxation_column=True)
        return self

    def tab_taxation_classification(self, ):
        # Show investments as classified on taxation (Debt, Hybrid/Other, Equity)
        investments_asr = [i for i in self.investments  if i.is_under_asr and not i.is_under_ltcg]
        investments_hybrid = [i for i in self.investments  if i.is_under_asr and i.is_under_ltcg]
        investments_cg = [i for i in self.investments  if i.is_under_stcg]

        self.show_data_block("Cap. Gains Tax Investments", investments_cg, self.value_total)
        self.show_data_block("Hybrid Tax Investments", investments_hybrid, self.value_total)
        self.show_data_block("Slab Rate Tax Investments", investments_asr, self.value_total)
        return self

    def tab_tags_classification(self, ):
        # Show investments as classified on Tags - <category>/<sub-category>
        tags = st.session_state.user.compiled_tags
        cats = sorted(tags.keys())
        tab1, tab2, tab3 = st.tabs(["Categories", "Sub-categories (All)", "Sub-categories (Category wise)"])
        with tab1:  # Tags classification -> Categories
            for cat in cats:
                investments = [i for i in self.investments if i.filter(selected_cats=[cat])]
                if not investments:
                    continue
                self.show_data_block(f"{cat} Investments", investments, self.value_total)
        with tab2:  # Tags classification -> Sub-categories (All)
            for n, cat in enumerate(cats):
                subs = sorted(tags[cat])
                if not subs:
                    continue
                for sub in subs:
                    investments = [i for i in self.investments if i.filter(selected_subs={cat:[sub]})]
                    if not investments:
                        continue
                    self.show_data_block(f"{cat}/{sub}", investments, self.value_total)
        with tab3:  # Tags classification -> Sub-categories (Category wise)
            cat_tabs = st.tabs(cats)
            for n, cat in enumerate(cats):
                subs = sorted(tags[cat])
                if not subs:
                    continue
                with cat_tabs[n]:
                    investments = [i for i in self.investments if i.filter(selected_cats=[cat])]
                    value_cat = sum(i.value for i in investments)
                    label = (f"₹{utils.number_str(value_cat, 2, compact="L")} ({len(investments)} "
                             f"MF scheme{"s" if len(investments) > 1 else ""})")
                    st.metric(value="", label=label, help="₹" + utils.number_str(value_cat))
                    for sub in subs:
                        investments = [i for i in self.investments if i.filter(selected_subs={cat:[sub]})]
                        if not investments:
                            continue
                        self.show_data_block(f"{sub}", investments, value_cat)

        return self

    def show_data_block(self, label, investments, ref_value=0, help_text="", taxation_column=False):
        value = sum(i.value for i in investments)
        ref_value = ref_value or self.value_total
        percent = value / ref_value * 100
        with ((st.container(horizontal=True, horizontal_alignment="left", ))):
            with st.container(width=150):
                st.write(f"###### {label}", )
                # st.caption("Value ₹" + utils.number_str(value, 2, compact="L", ))
                st.metric(label="Value ₹" + utils.number_str(value, 2, compact="L", ), value="",)
                st.metric(
                    label="% of Total",
                    value=utils.number_str(percent, 1, suffix='%'),
                    help=f"{percent:.1f}% of {utils.number_str(ref_value, )}",
                )
            if st.session_state.table_view_type == Investments.TABLE_VIEW_TYPES[0]:
                self.show_holdings_df(investments, taxation_column=taxation_column)
            elif st.session_state.table_view_type == Investments.TABLE_VIEW_TYPES[1]:
                with st.container(width=120):
                    st.metric(
                        label="Total XIRR",
                        value=utils.number_str(xirr(investments)*100, 1, suffix="%"),
                        help="Total Returns ₹" + utils.number_str(sum(i.get_total_pnl() for i in investments)),
                    )
                    st.metric(
                        label="Realized XIRR",
                        value=utils.number_str(xirr(investments, realized=True)*100, 1, suffix="%"),
                        help="Total Returns ₹" + utils.number_str(sum(i.get_realized_pnl() for i in investments)),
                    )
                    st.metric(
                        label="Unrealized XIRR",
                        value=utils.number_str(xirr(investments, unrealized=True)*100, 1, suffix="%"),
                        help="Total Returns ₹" + utils.number_str(sum(i.get_unrealized_pnl() for i in investments)),
                    )
                self.show_returns_df(investments, taxation_column=taxation_column)

        st.write("----")
        return self

    def show_returns_df(self, investments, taxation_column=False):
        values = [i.value for i in investments]
        realized_returns = [i.get_realized_pnl() for i in investments]
        realized_xirr = [i.realized_xirr() for i in investments]
        unrealized_returns = [i.get_unrealized_pnl() for i in investments]
        unrealized_xirr = [i.unrealized_xirr() for i in investments]
        taxes = [i.total_taxes_paid for i in investments]
        total_returns = [r+u for r, u, t in zip(realized_returns, unrealized_returns, taxes)]
        total_irr = [i.total_xirr() for i in investments]
        df = pd.DataFrame({
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
            df.insert(0, "Investor", pd.Series([i.investor.name.split()[0] for i in investments]))
        df["investments"] = [f"{i.scheme_name} /{i.folio}" for i in investments]
        formatted_df = df.style.format(
            utils.number_str,
            subset = ["values", "realized_returns", "unrealized_returns", "total_returns"],
        ).format(
            lambda i: utils.number_str(i*100, 1, suffix="%"), #+("" if float(i) == 0 else "%"),
            subset = ["realized_xirr", "unrealized_xirr", "total_xirr"],
        )

        column_config_df = {
            "investor": st.column_config.Column(label="Investor", width="small",),
            "values": st.column_config.Column(label="Market Value", width="small",),
            "realized_returns": st.column_config.Column(label="Realized Returns", width="small",),
            "unrealized_returns": st.column_config.Column(label="Unrealized Returns", width="small",),
            "total_returns": st.column_config.Column(label="Total Returns", width="small",),
            "realized_xirr": st.column_config.Column(label="Realized XIRR", width="small",),
            "unrealized_xirr": st.column_config.Column(label="Unrealized XIRR", width="small",),
            "total_xirr": st.column_config.Column(label="Total XIRR", width="small",),
            "investments": st.column_config.Column(label=f"Investments ({len(investments)})",
                                                   help="Scheme Name and Folio", width=250, pinned=True),
        }
        Investments.DF_COUNTER += 1
        st.dataframe(formatted_df, key=f"returns_df{Investments.DF_COUNTER}",
                     hide_index=True,
                     column_config=column_config_df,
                     on_select="rerun",
                     selection_mode="single-cell",
                     )
        return self


    def show_holdings_df(self, investments, taxation_column=False):
        df = pd.DataFrame()
        df["Investments"] = [f"{i.scheme_name} /{i.folio}" for i in investments]
        if taxation_column:
            df["Taxation"] = [i.taxation for i in self.investments]
        df["Value"] = [i.value for i in investments]
        value = df["Value"].sum()
        df["%"] = [(i.value / value) for i in investments]
        df["Units"] = [i.holding for i in investments]
        df["nav"] = [i.nav for i in investments]
        df["nav_date"] = [i.nav_date for i in investments]
        df["last_txn_type"] = [i.last_txn.type for i in investments]
        df["last_buy_date"] = [i.buy_txns[-1].txn_date for i in investments]
        df["last_sell_date"] = [(i.sell_txns[-1].txn_date if len(i.sell_txns) > 0 else None) for i in investments]

        column_config = {
            "Investments": st.column_config.TextColumn(label=f"Investments ({len(investments)})", pinned=True,
                                                       width=250, ),
            "nav_date": st.column_config.DateColumn(label=f"NAV Date", format="D-MMM-Y", ),
            "last_buy_date": st.column_config.DateColumn(label=f"Last buy date", format="D-MMM-Y", ),
            "last_sell_date": st.column_config.DateColumn(label=f"Last sell date", format="D-MMM-Y", ),
            "last_txn_type": st.column_config.TextColumn(label=f"Last txn type", ),
        }
        formatted_df = df.style.format({
            "Value": lambda x: utils.number_str(x),
            "%": lambda x: utils.number_str(x * 100, 1) + ("%" if float(x) > 0 else ""),
            "Units": lambda x: utils.number_str(x),
            "nav": lambda x: utils.number_str(x, 2),
            "last_txn_type": lambda x: x.title(),
        })
        # st.dataframe(formatted_df, hide_index=True, column_config=column_config)
        Investments.DF_COUNTER += 1
        selection = st.dataframe(formatted_df, key=f"returns_df{Investments.DF_COUNTER}",
                     hide_index=True,
                     column_config=column_config,
                     on_select="rerun",
                     selection_mode="single-cell",
                     )
        for cell in selection["selection"]["cells"]:
            st.write(investments[cell[0]].scheme_name, ",", cell[1])
        # st.write(selection["selection"]["cells"])
        # st.write(selection)
        return self


report = Investments()
(
    report.show_page_headings()
    .show_page_data()
 )
