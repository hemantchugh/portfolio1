import streamlit as st
from datetime import date, timedelta, datetime
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, List, Tuple
import pickle
import os
import utils.utils as utils
from model.mf_static import static_data, MfStatic

@dataclass
class Options:
    """Dataclass representing a User Options."""
    # selected_investors: List[Investor] = field(default_factory=list)
    hide_before_dates = [date.today(), utils.current_fy_start_date(), utils.previous_fy_start_date(), None]
    hide_zero_balance_disp_mssgs = ["Excluded investments having zero holding",
                                   "Included investments exited in current FY",
                                   "Included investments exited in previous FY",
                                   "Showing all current and past investments",
                                   ]
    zero_lanace_options_list = ["Exclude Zero Balance", "Include For Current FY", "Include For Previous FY",
               "Include All Investments"]
    selected_investors_names: List[str] = field(default_factory=list)
    selected_investor_name = None
    selected_zero_balance_option: int = 0
    hide_before_date: Optional[datetime.date] = date.today()
    hide_zero_balance_disp_mssg: str = hide_zero_balance_disp_mssgs[0]
    selected_fy = None
    # selected_tags: Dict[str, List[str]] = field(default_factory=dict)

    selected_cats: List[str] = field(default_factory=list)
    selected_subs: Dict[str, List[str]] = field(default_factory=dict)


class UserOptions:
    def __init__(self):
        self.investors = {}
        self.user = st.session_state.user
        self.filepath = self.user.datafolder / "options1.pkl"
        self.options = self._load()
        self.fy_options = utils.get_last_n_fy(n=4)
        self.fy_options.reverse()
        # self.options = load_options(self.user) or Options()

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
                    value= investor_name in self.options.selected_investors_names,
                    on_change=self._toggle_selected_investors, args=[investor_name],
                    width="stretch",
                )
        if len(self.options.selected_investors_names) == 0:
            st.warning("Select at least one!", icon="⚠️")

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

    def select_zero_balance_option(self):
        # with st.container():
        st.selectbox("Zero Balance Investments:",
                     options=[i for i in range(len(self.options.zero_balanace_options_list))],
                     format_func=lambda x: self.options.zero_lanace_options_list[int(x)],
                     key="zero_balance_option",
                     on_change=self._set_zero_balance_option,  # args=st.session_state.zero_balance_option,
                     index=self.options.selected_zero_balance_option or 0,
                     )

    def _set_zero_balance_option(self):
        self.options.selected_zero_balance_option = st.session_state.zero_balance_option
        self.options.hide_before_date = self.options.hide_before_dates[self.options.selected_zero_balance_option]
        self.options.hide_zero_balance_disp_mssg = self.options.hide_zero_balance_disp_mssgs[self.options.selected_zero_balance_option]
        # st.session_state["options"] = self.options
        # self._save()

    def _set_selected_cats(self):
        self.options.selected_cats = st.session_state.selected_cats
        # self._save()

    def _set_selected_subs(self, cat):
        if len(st.session_state[cat]) > 0:
            self.options.selected_subs[cat] = st.session_state[cat]
        else:
            del self.options.selected_subs[cat]
        self.options.selected_subs = {cat: subs for cat, subs in self.options.selected_subs.items() if len(subs)>0}
        # self._save()

    def clear_selected_cats_subs(self):
        self.options.selected_cats = []
        self.options.selected_subs = {}
        # for key, _ in self.options.selected_subs.items():
        #     self.options.selected_subs[key] = []
        # self._save()

    def select_tags(self):
        compiled_tags = st.session_state.user.compiled_tags
        selected_count = len(self.options.selected_cats)
        for cat, subs in self.options.selected_subs.items():
            selected_count += len(subs)

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
            st.button("Clear...",
                      type="tertiary",
                      # width: 70,
                      disabled=selected_count == 0,
                      on_click=self.clear_selected_cats_subs,
                      # width="stretch"
                      )

        for cat, subcat in compiled_tags.items():
            if len(subcat) > 0:
                st.pills(f"{cat} sub-categories:",
                         subcat,
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
        st.select_slider("Financial Year",
                         options = self.fy_options,
                         value=self.options.selected_fy or self.fy_options[-1],
                         key="selected_fy",
                         on_change=self._update_selected_fy,
                         format_func=lambda x: f"Current FY ({x})" if x == self.fy_options[-1]
                                        else f"Previous FY ({x})" if x == self.fy_options[-2] else f"FY {x}",
                         )
        self._update_selected_fy()
        # self.options.selected_fy = st.session_state.selected_fy

    def done(self):
        with st.container(horizontal=True, horizontal_alignment="center"):
            # if st.button("Cancel",):
            #     st.session_state.options = self._load()
            #     st.rerun()
            if st.button("Apply",):
                self._save()
                st.rerun()

    def _save(self):
        # self.options.selected_subs = {cat: subs for cat, subs in self.options.selected_subs.items() if len(subs)>0}
        # for cat, subs in self.options.selected_subs.items():
        #     if len(subs) > 0:
        st.session_state["options"] = self.options
        try:
            with open(self.filepath, "wb") as f:
                pickle.dump(self.options, f)
        except Exception:
            pass

    def _load(self):
        if "options" in st.session_state:
            self.options = st.session_state["options"]
        else:
            try:
                with open(self.filepath, "rb") as f:
                    self.options = pickle.load(f)
            except Exception:
                if os.path.exists(self.filepath):
                    os.remove(self.filepath)
                self.options = Options()
                self._init_options()
        return self.options

    def _init_options(self):
        self.options.selected_investors_names = [] # [investor.name for investor in self.user]
        self.options.selected_zero_balance_option = 0
        # self.options.selected_tags = {}
        self.options.selected_cats = []
        self.options.selected_subs = {}


@st.dialog("Options...", on_dismiss="ignore", dismissible=False)
def user_options(select_investors=False, select_zero_balance_options=False,
                 select_categories=False, select_fy=False, select_investor=False):

    # user_options = st.session_state.get("options") or UserOptions()
    user_options = UserOptions()
    if select_investors:
        user_options.select_investors()
    if select_investor:
        user_options.select_investor()
    if select_zero_balance_options:
        user_options.select_zero_balance_option()
    if select_categories:
        user_options.select_tags()
    if select_fy:
        user_options.select_fy()
    user_options.done()

