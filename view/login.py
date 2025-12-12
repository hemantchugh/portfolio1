import streamlit as st
import extra_streamlit_components as stx
from datetime import datetime, timedelta, date

import model.user as user_model

available_ids = user_model.get_all_user_ids()

# @st.fragment
# def get_manager():
#     return stx.CookieManager()
# cookie_manager = get_manager()
# cookies = cookie_manager.get_all()
# st.write("cookies", cookies)

def login():
    # st.session_state.user_id = get_cookie() or None
    # if st.session_state.user_id:
    #     st.rerun()

    with (st.container(horizontal=True, horizontal_alignment="center", )):
        with st.container(border=True, width=300, vertical_alignment="distribute", gap="large"):
            st.text_input("Please enter you user ID", key="user_id_input")
            with st.container(horizontal=True, horizontal_alignment="center"):
                st.button("Login", width=90,
                             on_click=set_user_id,
                             )

def set_user_id():
    if st.session_state.user_id_input in available_ids:
        st.session_state.user_id = st.session_state.user_id_input
        # set_cookie()
    else:
        confirm_new_id()

def new_id_yes():
    st.session_state.user_id = st.session_state.user_id_input
    # set_cookie()

# def get_cookie():
#     return cookie_manager.get(cookie="user")
#
# def set_cookie():
#     now = datetime.now()
#     cookie_manager.set("user", st.session_state.user_id, expires_at=datetime(now.year+1, month=now.month, day=now.day) )

def new_id_no():
    st.session_state.user_id = None

@st.dialog("Please confirm...", on_dismiss="rerun", dismissible=False)
def confirm_new_id():
    st.write("This ID does not exist. Want to create new user ID?")
    with st.container(horizontal=True, horizontal_alignment="center"):
        if st.button("Yes", key="new_id_yes", on_click=new_id_yes):
            st.rerun()
        if st.button("No", key="new_id_no", on_click=new_id_no):
            st.rerun()


login()