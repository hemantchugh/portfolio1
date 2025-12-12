import streamlit as st
import pandas as pd
from datetime import datetime, date

import utils.utils as utils
import model.investment_file as investment_file
import model.cas_json as cas_json
from model.investment import Investment

class InvData:
    def __init__(self, user_id):
        self.user_id = user_id
        self.investor_files = investment_file.get_all(user_id)

    def summary(self):
        # Investor name | #Investments | First Txn | Last Txn | Last Txn type | Last Txn Scheme
        if len(self.investor_files) < 1:
            st.write("No data is available. Please upload.")
            return self
        selection = {}
        investor_count = len(self.investor_files)
        st.write(f"Data available for {investor_count} investor{'s' if investor_count > 1 else ''}")
        for file in self.investor_files:
            all_txns = [t for inv in file.investments for t in inv.Transactions]
            first_txn = min(all_txns, key=lambda txn: txn.date)
            last_txn = max(all_txns, key=lambda txn: txn.date)
            sorted_investments = sorted(
                [inv for inv in file.investments if len(inv.Transactions) > 0],
                key=lambda inv: max(
                    (date.fromisoformat(t.date) for t in inv.Transactions if t.date),
                    default=date.min
                ),
                reverse=True
            )
            investor_heading = (f"{file.investor_name}: {len(sorted_investments)} Investments, "
                                f"from {datetime.strptime(first_txn.date, '%Y-%m-%d').strftime("%d-%b-%Y")} "
                                f"to {datetime.strptime(last_txn.date, '%Y-%m-%d').strftime("%d-%b-%Y")}"
                                )
            with st.expander(investor_heading, expanded=False):
                df = pd.DataFrame()
                mf_schemes = []
                folios = []
                ISINs = []
                from_dates = []
                to_dates = []
                last_txn_types = []
                balance_units = []
                for investment in sorted_investments:
                    txns = sorted(investment.Transactions, key=lambda t: t.date)
                    balance_units.append(utils.number_str(sum(round(t.quantity, 4) for t in txns),4))
                    folios.append(investment.Folio)
                    ISINs.append(investment.ISIN)
                    from_dates.append(txns[0].date)
                    to_dates.append(txns[-1].date)
                    last_txn_types.append(txns[-1].type)
                    mf_schemes.append(investment.SchemeName)
                scheme_column_name = f"MF Schemes ({len(mf_schemes)})"
                df[scheme_column_name] = mf_schemes
                df["ISIN"] = ISINs
                df["Folio"] = folios
                df["From"] = from_dates
                df["To"] = to_dates
                df["Last Txn"] = last_txn_types
                df["Balance Unit"] = balance_units
                # df.set_index(scheme_column_name, inplace=True)

                column_config = {
                    scheme_column_name: st.column_config.TextColumn(width=300, pinned=True),
                    "From": st.column_config.DateColumn(format="D-MMM-Y",),
                    "To": st.column_config.DateColumn(format="D-MMM-Y",),
                }
                selection = st.dataframe(df,
                             column_config=column_config,
                             hide_index=True,
                             on_select="rerun",
                             selection_mode=["single-column", "multi-row"],
                             )
                selected_investments = []
                # st.write(selection["selection"]["rows"])
                for row in selection["selection"]["rows"]:
                    selected_investments.append(sorted_investments[row])
                if selection["selection"]["columns"]:
                    selected_investments = sorted_investments
                # st.write(selected_investments)
                if st.button("Show Transactions",
                             disabled=(len(selected_investments) == 0),
                             type="tertiary",
                             key=file.investor_name):
                    show_transactions_popup(selected_investments)
        return self

@st.dialog("Transactions...", width="large")
def show_transactions_popup(investments):
    # Scheme Name /Folio | Date | Type | Units | Price | Tax | Source
    # Filter Criteria
    all_txns = [t for inv in investments for t in inv.Transactions]
    first_txn = min(all_txns, key=lambda txn: txn.date)
    last_txn = max(all_txns, key=lambda txn: txn.date)

    with st.container(horizontal=True, vertical_alignment="bottom", horizontal_alignment="distribute"):
        with st.container(horizontal=True, vertical_alignment="bottom"):
            filter_from = st.date_input("Filter From Date", value=first_txn.date,
                                        format="DD-MM-YYYY", width=140, key="filter_from",
                                        # disabled=(len(investments) == 1),
                                        )
            filter_to   = st.date_input("Filter To Date", value=last_txn.date,
                                        format="DD-MM-YYYY", width=140, key="filter_to",
                                        # disabled=(len(investments) == 1),
                                        )
        with st.container():
            filter_buy = st.checkbox("Show Buy Transactions", value =True, width=140, )
            filter_sell = st.checkbox("Show Sell Transactions", value =True, width=140, )
        with st.container():
            reverse_order = st.checkbox("Order Last to First", value =True, width=150,)
            last_txn_only = st.checkbox(f"Show Last Transaction{'s' if len(investments) > 1 else ''} Only", value =False, )
    with st.container():
        filter_like = st.text_input("Filter Scheme Name", disabled=(len(investments) == 1))
        filter_like = filter_like.lower()

    scheme_names = []; dates = []; types = []; units = []; prices = []; taxes = []; values = []; sources = []
    for investment in investments:
        txns = investment.Transactions
        for txn in txns:
            txn_date = datetime.strptime(txn.date, "%Y-%m-%d").date()
            filtered = (filter_from <= txn_date <= filter_to
                        and filter_like in investment.SchemeName.lower()
                        and ((txn.type == "buy" and filter_buy) or (txn.type == "sell" and filter_sell))
                        and (not last_txn_only or (last_txn_only and txn == txns[-1]))
                        )
            if filtered:
                scheme_names.append(f"{investment.SchemeName} /{investment.Folio}")
                dates.append(txn.date)
                units.append(txn.quantity)
                prices.append(txn.price)
                types.append(txn.type)
                taxes.append(txn.tax)
                values.append(txn.quantity * txn.price + txn.tax)
                sources.append(txn.source)
    df = pd.DataFrame()
    df["Date"] = dates
    df["Scheme Name"] = scheme_names
    df["Type"] = types
    df["Unit"] = units
    df["Price"] = prices
    df["Tax"] = taxes
    df["Value"] = values
    df["Source"] = sources
    df.sort_values("Date", ascending=not reverse_order, inplace=True)
    formatted_df = df.style.format(lambda x: utils.number_str(x, 4),
                         subset=["Unit", "Price",],
                   ).format(lambda x: utils.number_str(x, 2), subset=["Tax"]
                   ).format(lambda x: utils.number_str(x), subset=["Value"])

    column_config = {
        "Scheme Name": st.column_config.TextColumn(width=300, pinned=True),
        "Date": st.column_config.DateColumn(format="D-MMM-Y", pinned=True),
    }

    st.dataframe(formatted_df, column_config=column_config, hide_index=True)

    return

@st.dialog("Upload CAS PDF File", width="small", )
def cas_pdf_uploading():
    # with st.popover("Upload CAS file", width="stretch", icon=":material/upload:"):
    # with st.expander("Upload CAS file", width="stretch", icon=":material/upload:"):
    with st.form(key="upload_pdf", clear_on_submit=True, width="stretch"):
        cas_pdf_file = st.file_uploader("Upload CAS PDF File", type="pdf", key="cas_pdf_file", label_visibility="collapsed")
        pw = st.text_input(label='Password',
                           key='pw',
                           placeholder='CAS pdf Password',
                           type='password',
                           label_visibility="collapsed",
                           )
        submit = st.form_submit_button("Upload")
    if submit and cas_pdf_file is not None:
        with st.spinner('Parsing CAS pdf File...'):
            status = cas_json.pdf2json(st.session_state.user.user_id, cas_pdf_file, pw)
        st.toast(f"CAS PDF File {cas_pdf_file.name} Uploaded and Parsed Successfully", icon=":material/thumb_up:",
                 duration="long")
        st.balloons()

@st.dialog("Data Entry...", width="medium")
def manual_entry(investor_files):
    investors = [investor.investor_name for investor in investor_files]
    investors += ["New"]
    investor_file = None
    existing_investments = []
    selected_investment = None
    try:
        default_index = investors.index(st.session_state.options.selected_investor_name) or 0
    except Exception:
        default_index = 0
    with st.container(horizontal=True, vertical_alignment="bottom"):
        investor_name = st.radio("Select Investor", investors, horizontal=True, index=default_index)
        if investor_name != "New":
            investor = st.session_state.user.investors[investor_name]
            existing_investments = investor.investments
        else: # New selected
            investor_name = st.text_input("New Investor", key="investor_name", width=180,
                                          label_visibility="collapsed", placeholder="Enter Investor's Name"
                                          )
            investor_name = investor_name.strip()

    # investor_file = investment_file.get_one(st.session_state.user.user_id, investor_name)
    # existing_investments = [inv for inv in investor_file.investments]
    if not investor_name:
        return

    with st.container(horizontal=True, vertical_alignment="bottom"):
        include_sold_out = st.toggle("Include sold out investments", value=False, disabled=len(existing_investments) == 0)
        is_new_investment = st.toggle("New Investment", value=len(existing_investments) == 0, )

    if not is_new_investment:
        if not include_sold_out:
            existing_investments = [inv for inv in existing_investments if inv.holding > 0]

        with st.container(horizontal=False, vertical_alignment="bottom"):
            scheme_filter = st.text_input("Scheme Filter", label_visibility="collapsed",
                                          # width=320,
                                          placeholder="Scheme Name Filter",
                                          disabled=len(existing_investments) == 0)
            scheme_filter = scheme_filter.strip().lower()
            filtered_investments = [inv for inv in existing_investments
                                    if scheme_filter in inv.scheme_name.lower() or scheme_filter in inv.folio]
            selected_investment_index = st.selectbox("Select Investment", label_visibility="collapsed",
                         options=[i for i in range(len(filtered_investments))],
                         format_func=lambda i: f"{i+1}. {filtered_investments[i].scheme_short_name} /{filtered_investments[i].folio}",
                         )
        if len(filtered_investments) > 0 and selected_investment_index is not None:
            selected_investment = filtered_investments[selected_investment_index]
            i = selected_investment
            st.caption(f"{i.scheme_short_name} /{i.folio}, last {"Bought" if i.last_txn.type == "buy" else "Sold"} "
                       f"on {i.last_txn.txn_date.strftime('%d-%b-%Y')}")

    if is_new_investment:
        st.write("New Investment")

    with st.container(horizontal=True, vertical_alignment="bottom"):
        txn_type = st.radio("Select Transaction Type", ["Buy", "Sell"], index=0, label_visibility="collapsed")
        d_type = st.radio("Type", ["Amount", "Units"], index=0, label_visibility="collapsed")
        txn_date = st.date_input(f"{txn_type} Date", format="DD/MM/YYYY", max_value=date.today())
        label = f"{d_type} {"₹" if d_type=="Amount" else "Sold" if txn_type=="Sell" else "Bought"}"
        amount_or_units = st.number_input(label, format="%0.2f" if d_type == "Amount" else "%0.4f")
        price = st.number_input("Price (NAV)", format="%0.4f")

    units = amount_or_units / price if d_type == "Amount" and price > 0 else amount_or_units

    if st.button("Submit", disabled=not (amount_or_units > 0 and price > 0)):
        investor_file = investment_file.get_one(st.session_state.user.user_id, investor_name)
        investor_file.add_investment({
            "ISIN": selected_investment.isin,
            "Folio": selected_investment.folio,
            "SchemeName": selected_investment.scheme_name,
            "Transactions": [{'date':txn_date.strftime("%Y-%m-%d"), 'type':txn_type.lower(), 'quantity':units, 'price':price, 'tax':0, 'source':'manual'}],
        })
        investor_file.save()
        st.success("Submitted Investment/Transaction")
        del st.session_state.user

    # if isinstance(selected_investment, Investment):
    if not is_new_investment:
        st.write("Transactions of selected investment:", selected_investment.scheme_short_name)
        # Txn Date | Type | Units | NAV | Tax | Amount
        df = pd.DataFrame()
        df["txn_date"] = [txn.txn_date for txn in selected_investment.txns]
        df["Type"] = [txn.type for txn in selected_investment.txns]
        df["Units"] = [txn.units for txn in selected_investment.txns]
        df["Price"] = [txn.price for txn in selected_investment.txns]
        df["Tax"] = [txn.tax for txn in selected_investment.txns]
        df["Value"] = [txn.value for txn in selected_investment.txns]
        df.sort_values("txn_date", ascending=False, inplace=True)
        formatted_df = df.style.format(
            lambda x: utils.number_str(x, 4), subset=["Price", "Units"],
        ).format(
            lambda x: utils.number_str(x, ), subset=["Value"],
        )
        column_config = {"txn_date": st.column_config.DateColumn("Txn Date", format="DD/MM/YYYY",)}
        st.dataframe(formatted_df, column_config=column_config,  hide_index=True, height=200)



    # st.write("Correct entry")


def page_main():
    col1, col2 = st.columns([1, 5])
    # with col2:
    data = InvData(st.session_state.user.user_id).summary()
    # with col1:
    with st.container(horizontal=True,):
        if st.button("Upload CAS pdf file",):
            cas_pdf_uploading()
        if st.button("Manual Data Entry"):
            manual_entry(data.investor_files)



# tab1, tab2, tab3 = st.tabs(["Manual Entry", "Upload CAS", "Other"])
#
# with tab1:
# with tab2:

page_main()
