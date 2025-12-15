import streamlit as st
from datetime import datetime, timedelta, date

from model.user import User
import model.user as user_model
from model.options import Options
import view.income_dss as dss

st.set_page_config(page_title='Portfolio Analysis v0.9', layout="wide", page_icon="favicon.ico")

st.session_state["user_id"] = "Hemant"
# available_ids = user_model.get_all_user_ids()
# import extra_streamlit_components as stx
# def get_cookie():
#     return cookie_manager.get(cookie="user")
# def set_cookie():
#     now = datetime.now()
#     cookie_manager.set("user", st.session_state.user_id, expires_at=datetime(now.year+1, month=now.month, day=now.day) )
# @st.fragment
# def get_manager():
#     return stx.CookieManager()
# cookie_manager = get_manager()
# cookies = cookie_manager.get_all()
# st.session_state.user_id = get_cookie() or None
# if st.session_state.get("user_id"):
#     set_cookie()
# print(st.session_state.get("user_id"))
# import os
# st.write("CWD:", os.getcwd())
# st.write("Files here:", os.listdir("."))
# st.write("Files here:", os.listdir("data"))

if not st.session_state.get("user_id"):
    pages = st.navigation([st.Page("view/login.py", title="Login", icon=":material/chart_data:")])
elif "user" not in st.session_state:
    with (st.spinner(text='Loading data...')):
        user = User(st.session_state.user_id)
        st.session_state.user = user
        st.session_state.options = Options(user.datafolder)

if "user" in st.session_state:
    if len(st.session_state.user.investors) > 0:
        pages = st.navigation(
            pages ={
                "Reports": [
                st.Page("view/investments.py", title="Investments", ),
                st.Page("view/holding_details.py", title="Holding Details", ),
                st.Page("view/cons_returns.py", title="Consolidated Returns", ),
                st.Page("view/capital_gains.py", title="Realized/Tax Returns", ),
                # st.Page("view/income_dss.py", title="Income DSS", ),
                st.Page(dss.income_dss, title="Unrealized ASR Returns", ),
                st.Page(dss.stcg_dss, title="Unrealized Capital Gains", ),
            ],
                "Data Maintenance": [
                st.Page("view/inv_data_page.py", title="Upload/View Txn Data", ),
                st.Page("view/mf_master_page.py", title="MF Master Maintenance", ),
                ],
            },
            position="top",
        )
    else:
        pages = st.navigation([st.Page("view/inv_data_page.py", title="Upload/View Txn Data", icon=":material/chart_data:")])

# Adjust streamlit styles
adjust_streamlit_style = """
    <style>
    .stMainBlockContainer {padding: 70px; padding-top: 70px;} 
    </style>
"""
st.markdown(adjust_streamlit_style, unsafe_allow_html=True)

pages.run()