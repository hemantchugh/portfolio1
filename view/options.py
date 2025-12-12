import streamlit as st
from datetime import datetime
import utils.utils as utils
from model.options import ZERO_BALANCE_OPTIONS

class UserOptions:
    def __init__(self):
        # self.investors = {}
        self.user = st.session_state.user       # Instantiated once for each user in main.py
        self.options = st.session_state.options  # Instantiated once for each user in main.py

    # Selection of one of multiple investors - Checkboxes
    def _toggle_selected_investors(self, investor_name):
        if investor_name in self.options.selected_investors_names:
            self.options.selected_investors_names.remove(investor_name)
        else:
            self.options.selected_investors_names.append(investor_name)
        # If only one investor is selected, make single investor selection widget also reflect the same investor
        if len(self.options.selected_investors_names) == 1:
            self.options.selected_investor_name = self.options.selected_investors_names[0]

    def select_investors(self):
        investor_names = {investor.name: False for investor in self.user}
        st.write("Show investments for:")
        with st.container(horizontal=True):
            for investor_name in investor_names.keys():
                st.checkbox(
                    label=investor_name,
                    key=f"key-{investor_name}",
                    value= investor_name in self.options.selected_investors_names, # Boolean - checkbox
                    on_change=self._toggle_selected_investors, args=[investor_name],
                    width="stretch",
                )
        if len(self.options.selected_investors_names) == 0:
            st.warning("Select at least one!", icon="⚠️")

    # Selection of single investor - Radio input
    def _toggle_selected_investor(self):
        self.options.selected_investor_name = st.session_state.selected_investor_name
        # If multi investor selection widget has only one or No investor is selected, make that same investor as in single investor widget
        if len(self.options.selected_investors_names) < 2:
            self.options.selected_investors_names = [self.options.selected_investor_name]

    def select_investor(self):
        investor_names = [investor.name for investor in self.user]
        st.radio("Select one:",
                 options=investor_names,
                 index=investor_names.index(self.options.selected_investor_name) if
                            self.options.selected_investor_name else 0,
                 key="selected_investor_name",
                 horizontal=True,
                 on_change=self._toggle_selected_investor,
                 )
        self._toggle_selected_investor()

    # Inclusion/Exclusion of sold out MF schemes (investments)
    def _set_zero_balance_option(self):
        selected_option = st.session_state.zero_balance_option
        self.options.selected_hide_before_date = ZERO_BALANCE_OPTIONS[selected_option]["hide_before_date"]

    def select_zero_balance_option(self):
        index = next(
            (i for i, d in enumerate(ZERO_BALANCE_OPTIONS) if d["hide_before_date"] ==
             self.options.selected_hide_before_date),
            0  # returned if not found
        )
        st.selectbox("Zero Balance Investments:",
                     options=[i for i in range(len(ZERO_BALANCE_OPTIONS))],
                     format_func=lambda x: ZERO_BALANCE_OPTIONS[int(x)]["selection_text"],
                     key="zero_balance_option",
                     on_change=self._set_zero_balance_option,  # args=st.session_state.zero_balance_option,
                     index=index,
                     )


    # Selection of categories and subcategories (extracted/compiled from user entered tags in mf_master)
    def _set_selected_cats(self):
        self.options.selected_cats = st.session_state.selected_cats

    def _set_selected_subs(self, cat):
        if len(st.session_state[cat]) > 0:
            # If there is any selection(s)
            self.options.selected_subs[cat] = st.session_state[cat]
        else:
            # If no selections, remove the category from selected_subs Dict
            del self.options.selected_subs[cat]
            # format of selected_subs = Dict{cat:str : subs:List("str")]}
        self.options.selected_subs = {cat: subs for cat, subs in self.options.selected_subs.items() if len(subs)>0}

    def clear_selected_cats_subs(self):
        # Clear all selections
        self.options.selected_cats = []
        self.options.selected_subs = {}

    def select_tags(self):
        compiled_tags = st.session_state.user.compiled_tags
        with st.container(horizontal=True, horizontal_alignment="distribute"):
            st.pills("Main Categories:",
                     compiled_tags.keys(),
                     selection_mode="multi",
                     on_change=self._set_selected_cats,
                     # default=st.session_state.user.options.selected_cats,
                     default=self.options.selected_cats,
                     format_func=lambda x: x.title(),
                     key="selected_cats",
                     )

            selected_count = len(self.options.selected_cats) + len(self.options.selected_subs)
            # for cat, subs in self.options.selected_subs.items():
            #     selected_count += len(subs)
            st.button("Clear...", type="tertiary", disabled=selected_count == 0,
                      on_click=self.clear_selected_cats_subs,)

        for cat, subs in compiled_tags.items():
            if len(subs) > 0:
                st.pills(f"{cat} sub-categories:",
                         subs,
                         selection_mode="multi",
                         on_change=lambda x: self._set_selected_subs(x), args=[cat],
                         default=self.options.selected_subs.get(cat) or [],
                         disabled=cat in self.options.selected_cats,
                         # default=st.session_state.user.options.selected_subs.get(cat) or [],
                         # format_func=lambda x: x.title(),
                         key=cat,
                         )

    def _update_selected_fy(self):
        self.options.selected_fy = st.session_state.selected_fy

    def select_fy(self):
        fy_options = utils.get_last_n_fy(n=4)
        fy_options.reverse()
        st.select_slider("Financial Year",
                         options = fy_options,
                         value=self.options.selected_fy or fy_options[-1],
                         key="selected_fy",
                         on_change=self._update_selected_fy,
                         format_func=lambda x: f"Current FY ({x})" if x == fy_options[-1]
                                        else f"Previous FY ({x})" if x == fy_options[-2] else f"FY {x}",
                         )
        self._update_selected_fy()

    def done(self):
        with st.container(horizontal=True, horizontal_alignment="center"):
            if st.button("Cancel",):
                self.options.discard_changes()
                st.rerun()
            if st.button("Apply", disabled=not self.options.has_unsaved_changes()):
                self.options.save()
                st.rerun()


@st.dialog("Options...", on_dismiss="ignore", dismissible=False)
def user_options(select_investors=False, select_zero_balance_options=False,
                 select_categories=False, select_fy=False, select_investor=False):
    options = UserOptions()
    if select_investors:
        options.select_investors()
    if select_investor:
        options.select_investor()
    if select_zero_balance_options:
        options.select_zero_balance_option()
    if select_categories:
        options.select_tags()
    if select_fy:
        options.select_fy()
    options.done()

