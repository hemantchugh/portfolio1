from operator import ifloordiv

import streamlit as st
from datetime import date, timedelta

import utils.utils as utils
from model.mf_static import static_data, MfStatic

class SidebarOptions:
    def __init__(self):
        self.selected_tax_treatments = []
        self.selected_mf_categories = []
        self.selected_fin_year = None
        # self.zero_balance_option = 0

        self.selected_hide_zero_balance_before_date = None
        self.mf_static = MfStatic().load()

    def show_options(self, investor,
                    get_tax_treatment=False,
                    get_mf_category=False,
                    get_fin_year=False,
                    default_fy=None,
                    get_hide_zero_balance_before_date=False,
                    zero_balance_option_default=0,
                    ):

        st.session_state.selected_mf_categories = self.selected_mf_categories
        st.session_state.selected_tax_treatments = self.selected_tax_treatments
        if get_fin_year and "selected_fin_year" not in st.session_state:
            st.session_state.selected_fin_year = self.selected_fin_year \
                if self.selected_fin_year is not None else default_fy

        if get_hide_zero_balance_before_date and "zero_balance_option" not in st.session_state:
            st.session_state.selected_zero_balance_option = zero_balance_option_default
        if  "zero_balance_option" in st.session_state:
            # Hack to retain the selected field value - needed every time field needs to be displayed
            st.session_state.selected_zero_balance_option = st.session_state.selected_zero_balance_option

        fy_options = utils.get_last_n_fy(n=4)
        zero_balance_options = ["Exclude Zero Balance", "Include For Current FY", "Include For Previous FY", "Include All Investments"]
        hide_before_dates = [date.today(), utils.current_fy_start_date(), utils.previous_fy_start_date(), None]

        # This is to make Tax Treatment selection and MF Categories selection mutually axclusive
        if "selected_tax_treatments" not in st.session_state:
            st.session_state["selected_tax_treatments"] = []
        if "selected_mf_categories" not in st.session_state:
            st.session_state["selected_mf_categories"] = []
        selected_tax_treatments = st.session_state["selected_tax_treatments"]
        selected_mf_categories = st.session_state["selected_mf_categories"]


        container = None
        if get_tax_treatment or get_mf_category or get_fin_year or get_hide_zero_balance_before_date:
            container = st.sidebar.expander("Filters", expanded=True, )

        if get_hide_zero_balance_before_date:
            container.selectbox("Zero Balance Investments:",
                                        options=[i for i in range(len(zero_balance_options))],
                                        format_func=lambda x: zero_balance_options[int(x)],
                                        key="zero_balance_option",
                                      )
            self.selected_hide_zero_balance_before_date = hide_before_dates[st.session_state.selected_zero_balance_option]


        investments = investor.get_filtered_investments(
            hide_zero_balance_before=(hide_before_dates[st.session_state.selected_zero_balance_option]
                                               if ("zero_balance_option" in st.session_state)
                                                    # and get_hide_zero_balance_before_date
                                      else date.today()),
            # sold_in_fy=st.session_state.selected_fin_year if "selected_fin_year" in st.session_state else None,
        )
        available_tax_treatments = sorted(set([i.tax_treatment for i in investments]))
        available_mf_categories = sorted(set([i.mf_category for i in investments]))


        # st.session_state["selected_tax_treatments"] = ["Equity", "Hybrid"]
        if get_tax_treatment:
            self.selected_tax_treatments = container.segmented_control(
                "Tax Treatment",
                # options=self.mf_static.tax_treatment,
                options=available_tax_treatments,
                selection_mode="multi",
                disabled=any(selected_mf_categories),
                key = "selected_tax_treatments",
                width="stretch",
                on_change=self.set_tax_treatments
            )

        if get_mf_category:
            self.selected_mf_categories = container.pills(
                "MF Categories",
                # options=self.mf_static.mf_category,
                options=available_mf_categories,
                selection_mode="multi",
                disabled=any(selected_tax_treatments),
                key = "selected_mf_categories",
                on_change=self.set_mf_categories
                # default=self.selected_mf_categories
            )

        if get_fin_year:
            self.selected_fin_year = container.selectbox("Financial Year",
                                                        fy_options,
                                                        key="selected_fin_year",
                                                        index=fy_options.index(default_fy) if default_fy in fy_options else None,
                                                        placeholder="Choose FY",
                                                        # format_func=lambda x: "All" if x is None else x,
                                                        # default=default_fy
                                                        )

    def get_tax_treatments(self):
        pass

    def get_categories(self):
        pass

    def set_mf_categories(self):
        self.selected_mf_categories = st.session_state["selected_mf_categories"]

    def set_tax_treatments(self):
        self.selected_tax_treatments = st.session_state["selected_tax_treatments"]

    def set_zero_balance_option(self):
        self.zero_balance_option = st.session_state["zero_balance_option"]

    def set_selected_fin_year(self):
        self.selected_fin_year = st.session_state["selected_fin_year"]

def update_investor_name():
    st.session_state.user.set_selected_investor(st.session_state.investor_names_radio)
    # st.session_state.investor_names_radio = st.session_state.investor_names_radio

def choose_investor():
    # This is required to correctly set the selected radio button every time.
    st.session_state.investor_names_radio = st.session_state.user.selected_investor.name

    investor_names = [investor.name for investor in st.session_state.user]
    if len(investor_names) > 1:  # If there are more than 1 investors for the user...
        # investors_container =
        with st.sidebar.expander(label='Investor: ' + st.session_state.user.selected_investor.name):
        # with st.sidebar.popover('Investor: ' + st.session_state.user.selected_investor.name, width="stretch"):
            st.radio(label="Select investor",
                 # options=[investor.name for investor in st.session_state.user],
                 options=investor_names,
                 key="investor_names_radio",
                 label_visibility="collapsed",
                 on_change=update_investor_name,
                 )


def compile_tags(tags: list[str]) -> dict[str, list[str]]:
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