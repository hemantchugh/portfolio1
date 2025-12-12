import streamlit as st
import pandas as pd
from pathlib import Path

import utils.utils as utils
from model.mf_master import MFSchemeMaster
import utils.sidebar_options as sidebar_options

class MFMasterPage:
    def __init__(self):
        self.mf_master = None
        self.mf_master_list = None
        self.df1 = None
        self.edited_df = None

    def prepare_df1(self):
        user_id = st.session_state.user.user_id
        # self.filepath = Path("data") / user_id / "mf_master.json"
        self.mf_master = MFSchemeMaster(user_id)
        mf_master_list = self.mf_master.get_all_schemes() # .values()
        self.mf_master_list = sorted(mf_master_list, key=lambda x: x.last_txn_date, reverse=True)
        df1 = pd.DataFrame({})
        df1["#"] = [i+1 for i in range(len(mf_master_list))]
        df1["isin"] = [scheme.isin for scheme in self.mf_master_list]
        df1["last_txn_date"] = [scheme.last_txn_date for scheme in self.mf_master_list]
        df1["scheme_name"] = [scheme.scheme_name for scheme in self.mf_master_list]
        df1["is_under_ltcg"] = [scheme.is_under_ltcg for scheme in self.mf_master_list]
        df1["is_under_stcg"] = [scheme.is_under_stcg or None for scheme in self.mf_master_list]
        df1["is_under_asr"] = [scheme.is_under_asr for scheme in self.mf_master_list]
        # df1["tax_treatment"] = [scheme.tax_treatment for scheme in self.mf_master_list]
        df1["exit_load_days"] = [scheme.exit_load_days for scheme in self.mf_master_list]
        # df1["ltcg_days"] = [scheme.ltcg_days for scheme in self.mf_master_list]
        df1["tags"] = [scheme.tags for scheme in self.mf_master_list]
        df1.set_index("last_txn_date", inplace=True)
        self.df1 = df1

        self.formatted_df1 = self.df1.style.format({
            # "tags": lambda x: x if len(x) > 0 else [None],
        })
        self.column_config_df1 = {
            "#": st.column_config.Column(
                # label=f"Scheme Name ({len(self.mf_master_list)})",
                help=f"Sequence",
                width=10,
                disabled=True,
            ),
            "scheme_name": st.column_config.Column(
                label=f"Scheme Name ({len(self.mf_master_list)})",
                help=f"You can make changes to the scheme name",
                width=300,
            ),
            "last_txn_date": st.column_config.Column(
                label=f"Last Txn Date",
                # help=f"You can make changes to the scheme name",
                # width=300,
            ),
            "is_under_stcg": st.column_config.CheckboxColumn(
                label=f"STCG Tax",
                help="Is STCG Tax applicable on this scheme (Autocomputed)",
                disabled=True,
            ),
            "is_under_ltcg": st.column_config.CheckboxColumn(
                label=f"LTCG Tax?",
                help="Is LTCG Tax applicable on this scheme?",
            ),
            "is_under_asr": st.column_config.CheckboxColumn(
                label=f"ASR Tax?",
                help="Is Applicable Slab Rate Tax applicable on this scheme?",
            ),
            "exit_load_days": st.column_config.NumberColumn(
                label="Load Days",
                help="Number of days until exit load",
                min_value=0,
                max_value=365*5,
            ),
            "tags": st.column_config.ListColumn(
                label="Tags",
                help="You may enter multiple tags in formats <category> or <category>/<subcategory>",
                width=250,
                # default=None,
                required=True,
            )
        }
        # self.formatted_df = self.df
        return self


    def show_df1(self):
        st.sidebar.empty()
        if len(self.df1) > 0:
            self.edited_df = st.data_editor(
                self.formatted_df1, column_config=self.column_config_df1,
                # hide_index=True,
                column_order=["#", "scheme_name", "is_under_stcg", "is_under_ltcg", "is_under_asr", "exit_load_days", "tags"],
                key="edited_master_df",
               )
            with st.container(horizontal=True, horizontal_alignment="distribute"):
                with st.container():
                    # Inform user (for saving) if data has been changed.
                    changes_count = len(st.session_state.edited_master_df["edited_rows"].values())
                    if changes_count:
                        st.caption(f"You have unsaved changes in {changes_count} rows.")
                    if st.button("Save Changes") and len(st.session_state.edited_master_df["edited_rows"]) > 0:
                        self.edited_df.reset_index(inplace=True)
                        self.mf_master.save_from_df(self.edited_df)
                        del st.session_state["user"]        # Force reloading of data
                        st.rerun()
                with st.container():
                    st.caption(f"<div style='text-align: right; font-size: 0.9rem; color:black; font-weight:400;'> "
                               f"Total schemes: {len(self.mf_master_list)}</div>",
                               unsafe_allow_html=True, )
                    count = len(self.df1[self.df1["exit_load_days"].isnull()])
                    st.caption(f"<div style='text-align: right; font-size: 0.9rem; color:black; font-weight:400;'>"
                               f"Exit-load days missing for {count} schemes</div>",
                               unsafe_allow_html=True, )
                    count = self.df1[
                        (self.df1["is_under_stcg"].isnull() | (self.df1["is_under_stcg"] == False)) &
                        (self.df1["is_under_ltcg"].isnull() | (self.df1["is_under_ltcg"] == False)) &
                        (self.df1["is_under_asr"].isnull() | (self.df1["is_under_asr"] == False))
                        ].shape[0]
                    st.caption(f"<div style='text-align: right; font-size: 0.9rem; color:black; font-weight:400;'>"
                               f"Tax details missing for {count} schemes</div>",
                               unsafe_allow_html=True, )
                    count = self.df1[self.df1["tags"].isnull() | self.df1["tags"].apply(lambda x: isinstance(x, list) and len(x) == 0)].shape[0]
                    st.caption(f"<div style='text-align: right; font-size: 0.9rem; color:black; font-weight:400;'>"
                               f"Tags missing for {count} schemes</div>",
                               unsafe_allow_html=True, )
        else:
            st.dataframe(self.df1, column_config=self.column_config_df1, hide_index=True,
                               column_order=["#", "scheme_name", "tax_treatment", "exit_load_days", "ltcg_days", "tags"])
        return self

    def show_tags(self):
        st.sidebar.write("### Your MF Categories Structure:")
        tags = []
        for _, row in self.edited_df.iterrows():
            if isinstance(row.tags, list):
                for tag in row.tags:
                    tags.append(tag)
        compiled_tags = sidebar_options.compile_tags(tags)
        # st.sidebar.write(compiled_tags)
        pills_container = st.sidebar.container()

        if "categories" not in st.session_state:
            st.session_state.categories = []
        selected_count = len(st.session_state.categories)
        for cat, subcat in compiled_tags.items():
            if len(subcat) > 0:
                if f"subcat of {cat}" not in st.session_state:
                    st.session_state[f"subcat of {cat}"] = []
                selected_count += len(st.session_state[f"subcat of {cat}"])

        if selected_count > 0:
            if st.sidebar.button("Clear Filter Selection",
                                 type="tertiary",
                                 # disabled=selected_count == 0,
                                 width="stretch"
                                 ):
                st.session_state.categories = []
                for cat, subcat in compiled_tags.items():
                    if len(subcat) > 0:
                        st.session_state[f"subcat of {cat}"] = []
                st.rerun()

        with pills_container:
            st.pills("Main Categories:",
                             compiled_tags.keys(),
                             selection_mode="multi",
                             # format_func=lambda x: x.title(),
                             key="categories",
                             )
            # st.write('---')
            st.divider()
            for cat, subcat in compiled_tags.items():
                if len(subcat) > 0:
                    st.pills(f"{cat} sub-categories:",
                             subcat,
                             selection_mode="multi",
                             # format_func=lambda x: x.title(),
                             key=f"subcat of {cat}",
                             )
                    st.write('---')

            if len(st.session_state.edited_master_df["edited_rows"].values()) > 0:
                if st.sidebar.button("Save Changes", width="stretch") and len(st.session_state.edited_master_df["edited_rows"]) > 0:
                    self.edited_df.reset_index(inplace=True)
                    self.mf_master.save_from_df(self.edited_df)
                    # st.rerun()

        #     scheme = MFScheme(
        #         isin=row["isin"],
        #         scheme_name=row["scheme_name"],
        #         tax_treatment=row["tax_treatment"],
        #         exit_load_days=row["exit_load_days"],
        #         ltcg_days=row["ltcg_days"],
        #         tags=row["tags"] or [],
        #         last_txn_date=row["last_txn_date"],
        #       )
        #     schemes[scheme.isin] = scheme
        # self.schemes = schemes

        # for mf_master_scheme in self.mf_master_list:
        #     # st.sidebar.write(mf_master_scheme.tags)
        #     if isinstance(mf_master_scheme.tags, list):
        #         for tag in mf_master_scheme.tags:
        #             st.sidebar.markdown(tag)


page = MFMasterPage()
page.prepare_df1().show_df1()
page.show_tags()

