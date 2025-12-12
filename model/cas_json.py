# Parse CAS pdf and save as cas data as json file
import re, logging
import time
from pypdf import PdfReader
from pprint import pprint
import pandas as pd
import os
from datetime import datetime, date

import utils.utils as utils
from model.investment_file import InvestmentFileManager

start_time = time.time()

CAS_TEXT_FILE = r'data/cas/cas.txt'

def pdf2txt(pdf_file, pw):
    # Read CAS File text data
    text = ''
    page_count = 0
    reader = PdfReader(pdf_file)
    if reader.is_encrypted and not pw:
        return 'Password Required'
    if reader.is_encrypted and pw:
        if reader.decrypt(pw) == 0:
            raise ValueError("Wrong password or unable to decrypt the PDF.")

    logging.getLogger("pypdf").setLevel(logging.ERROR)

    for page in reader.pages:
        # The parameters passed to extract_text function are important
        text += page.extract_text(extraction_mode="layout", layout_mode_scale_weight=1.0)
    page_count = len(reader.pages)

    # Enable pypdf logger to show warnings again (suppressed temporarily above)
    logging.getLogger("pypdf").setLevel(logging.WARNING)

    print(f'Extracted {page_count} page(s), {len(text)} characters from {pdf_file.name}.')
    return text

def save_cas_text_file(text, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(text)
    return text

def sanitize_scheme_name(name):
    name = re.sub(r'\s*\(([Ff]ormerly|Non-Demat|[eE]rstwhile).*?\).*', '', name)
    name = name.title()
    name = re.sub(r'( Plan| Option)', '', name)
    # name = re.sub(r'(\s?-\s?| Fund )', ' ', name)
    name = name.replace('Direct', 'Dir')
    return name.strip()

def get_statement_dates(lines):
    cas_heading = cas_from_date = cas_to_date = None
    cas_heading_patter = re.compile(r'^ *Consolidated Account Statement')
    # cas_dates_pattern = re.compile(r'^ *([0-3]\d-[A-Z][a-z]{2}-20[0-4]\d) To ([0-3]\d-[A-Z][a-z]{2}-20[0-4]\d)')
    cas_dates_pattern = re.compile(r'^ *([0-3]\d-[A-Z][a-z]{2}-\d{4}) To ([0-3]\d-[A-Z][a-z]{2}-20[0-4]\d)')
    while lines:
        match = cas_heading_patter.search(lines[0])
        # cas_heading = match.group(1)
        if match:
            match = cas_dates_pattern.search(lines[1])
            if match:
                cas_from_date = match.group(1)
                cas_to_date = match.group(2)
                # cas_from_date = datetime.strptime(match.group(1), "%d-%b-%Y").date()
                # cas_to_date = datetime.strptime(match.group(2), "%d-%b-%Y").date()
                break
            else:
                raise Exception('CAS dates not found after the CAS heading statement')
        del lines[0]
    if not lines:
        raise Exception('Parsed entire file but CAS heading not found')
    return cas_from_date, cas_to_date

def get_next_investment(lines):
    """
    Fetch next Investment from text lines extracted from CAS dpf file
    1. Search lines for Folio regex pattern
    1a. delete consumed lines
    1b. If end of lines[], return blank
    2. extract isin, name and amfi code from next 2,3 lines based on their regex patterns
    3. Delete the consumed text lines
    4. Return extracted data values
    :param lines:
    :return:
    """
    folio = None
    isin = None
    scheme_name = None
    amfi = None
    pan = None
    name = None
    folio_pattern = re.compile(r'Folio No: (\d+)')
    pan_pattern = re.compile(r'PAN: ?([A-Z0-9]{10})')
    name_pattern = re.compile(r'^ ?([A-Za-z. ]+$)')
    scheme_isin_pattern = re.compile(r'^([A-Z0-9]{3,})-([A-Za-z]{2,}.*)\s?-\s?ISIN:\s?(INF[A-Z0-9]{9})')

    # while lines and not folio:
    while lines and (folio is None or isin is None):
        match = folio_pattern.search(lines[0])
        if match:       # We found Folio
            folio = match.group(1)

            match = pan_pattern.search(lines[0])
            if match:
                pan = match.group(1)

            match = name_pattern.search(lines[1])
            if match:
                name = match.group(1)

            scheme_name_lines = re.sub(r'\s+Registrar : CAMS', '', lines[2] + lines[3])  # searched lines are w.r.t. folio line
            match = scheme_isin_pattern.search(scheme_name_lines)
            if match:
                amfi = match.group(1)
                scheme_name = sanitize_scheme_name(match.group(2))
                isin = match.group(3)
            else:  # ISIN / Scheme name not found
                pass
                # We need to save this in the log file - Actually there are some old funds for which ISIN
                # is not present in the CAMS report
                # raise Exception(f'ISIN pattern did not match for', folio, 'in line:\n', scheme_name_lines)
            if scheme_name is not None and 'Segregated' in scheme_name:
                # ***** Ignore segregated folios **** (Were specially created for Franklin Tempn in 2020)
                folio = None
        del lines[0]
    # name = ' '.join(name.split())
    return isin, folio, scheme_name, name, pan

def parse_for_investment_txns(lines, isin, folio):
    """
    Extract transactions from text lines:
    - Search for line with "Opening Balance"
    - Scan lines with buy and sell transactions till we reach line with "Closing Balance"
    - Compare running total of units with closing balance
    """
    opening_balance = 0.0
    closing_balance = 0.0
    buy_txns = []
    sell_txns = []
    txn_date = None
    first_txn_date = None
    last_txn_date = None
    running_total = 0.0

    opening_balance_pattern = re.compile(r'Opening Unit Balance: (\d*,?\d+\.\d+)')
    closing_balance_pattern = re.compile(r'Closing Unit Balance: (\d*,?\d+\.\d+)')
    buy_txn_pattern = re.compile(
        # r'^([0-3]\d-[A-Z][a-z]{2}-20[0-4]\d) .*?(Purchase|Switch[- ]\w?[Ii]n|Investment|S T P In|Lateral Shift In).*? (\d{1,3}(?:,\d{3})*\.\d+) *(\d{1,3}(?:,\d{3})*\.\d+) *(\d{1,3}(?:,\d{3})*\.\d+) *(\d{1,3}(?:,\d{3})*\.\d+)$')
        r'^([0-3]\d-[A-Z][a-z]{2}-20[0-4]\d) .*?(Purchase|Switch.*?[Ii]n|Investment|S T P In|Lateral Shift In).*? (\d{1,3}(?:,\d{3})*\.\d+) *(\d{1,3}(?:,\d{3})*\.\d+) *(\d{1,3}(?:,\d{3})*\.\d+) *(\d{1,3}(?:,\d{3})*\.\d+)$')
    # Issue with negative units with transaction "Systematic Purchase Reversed" for HSBC Small Cap Fund
    # Looks like we have to ignore the transaction type text and solely rely on units amount. But this ignores case of Purchase Reversals...
    # Purchase Reversals need to be captured separately

    # => **** If date is same as prev txn and units is reverse (-ve) then it is a reversal transaction ***********
    sell_txn_pattern = re.compile(
        # r'^([0-3]\d-[A-Z][a-z]{2}-20[0-4]\d) .*?(Redemption|Switch[- ][Oo]ut|S T P Out|Lateral Shift Out|Withdrawal).*? \((\d{1,3}(?:,\d{3})*\.\d+)\) *\((\d{1,3}(?:,\d{3})*\.\d+)\) *(\d{1,3}(?:,\d{3})*\.\d+) *(\d{1,3}(?:,\d{3})*\.\d+)$')
        r'^([0-3]\d-[A-Z][a-z]{2}-20[0-4]\d) .*?(Redemption|Switch.*?[Oo]ut|S T P Out|Lateral Shift Out|Withdrawal).*? \((\d{1,3}(?:,\d{3})*\.\d+)\) *\((\d{1,3}(?:,\d{3})*\.\d+)\) *(\d{1,3}(?:,\d{3})*\.\d+) *(\d{1,3}(?:,\d{3})*\.\d+)$'
    )

    purchase_reversal_pattern = re.compile(
        r'^([0-3]\d-[A-Z][a-z]{2}-20[0-4]\d) .*?(Revers[ed|al]|[Rr]ejection).*? \((\d{1,3}(?:,\d{3})*\.\d+)\) *\((\d{1,3}(?:,\d{3})*\.\d+)\) *(\d{1,3}(?:,\d{3})*\.\d+) *(\d{1,3}(?:,\d{3})*\.\d+)$')


    stamp_duty_pattern = re.compile(r'^([0-3]\d-[A-Z][a-z]{2}-20[0-4]\d) .*? Stamp Duty .*? (\d{1,3}(?:,\d{3})*\.\d+)$')
    stt_paid_pattern = re.compile(r'^([0-3]\d-[A-Z][a-z]{2}-20[0-4]\d) .*? STT Paid .*? (\d{1,3}(?:,\d{3})*\.\d+)$')


    opening_balance_found = False
    closing_balance_found = False

    while lines and not opening_balance_found:
        match = opening_balance_pattern.search(lines[0])
        if match:
            opening_balance_found = True
            opening_balance = float(match.group(1).replace(',', ''))
            running_total = opening_balance
        del lines[0]
    if opening_balance_found:
        while lines and not closing_balance_found:
            match = buy_txn_pattern.search(lines[0])
            if match:
                # txn_date = match.group(1)  # Let the date be str
                txn_date = datetime.strptime(match.group(1), "%d-%b-%Y").strftime("%Y-%m-%d")
                units = float(match.group(4).replace(',', ''))
                price = float(match.group(5).replace(',', ''))
                buy_txns.append({"date":txn_date, "type":"buy", "quantity":units,
                                 "price":price, "tax":0, "source":"eCas"})    # 0 is place holder for stamp duty

                units_balance = float(match.group(6).replace(',', ''))
                running_total = round(running_total + units, 4)

            match = stamp_duty_pattern.search(lines[0])
            if match:
                txn_date = match.group(1)  # Let the date be str
                stamp_duty = float(match.group(2))
                buy_txns[-1]["tax"] = stamp_duty

            match = purchase_reversal_pattern.search(lines[0])
            if match:
                txn_date = match.group(1)  # Let the date be str
                txn_date = datetime.strptime(match.group(1), "%d-%b-%Y").strftime("%Y-%m-%d")
                units = float(match.group(4).replace(',', ''))
                running_total = round(running_total - units, 4)
                # buy_txns[txn_date]['units'] -= units
                # if buy_txns[txn_date]['units'] == 0:
                if buy_txns[-1]["date"] == txn_date and buy_txns[-1]["quantity"] == units:
                    del buy_txns[-1]
                else:
                    # raise exception
                    print("Reversal transaction not successful!!!!")
                    raise Exception("Reversal transaction not successful!!!! for ISIN", isin, "Folio", folio)

            match = sell_txn_pattern.search(lines[0])
            if match:
                txn_date = match.group(1)  # Let the date be str
                txn_date = datetime.strptime(match.group(1), "%d-%b-%Y").strftime("%Y-%m-%d")
                units = float(match.group(4).replace(',', ''))
                price = float(match.group(5).replace(',', ''))
                sell_txns.append({"date":txn_date, "type":"sell", "quantity": units * -1, "price": price, "tax":0, "source":"eCas"}) # 0 is placeholder for STT

                units_balance = float(match.group(6).replace(',', ''))
                running_total = round(running_total - units, 4)

            match = stt_paid_pattern.search(lines[0])
            if match and sell_txns:
                txn_date = match.group(1)  # Let the date be str
                stt = float(match.group(2))
                sell_txns[-1]["tax"] = stt

            match = closing_balance_pattern.search(lines[0])
            if match:
                closing_balance_found = True
                closing_balance = float(match.group(1).replace(',', ''))
                if running_total != closing_balance:
                    print(
                        f'Folio: {folio}, ISIN: {isin} => Running Total: {running_total}, Closing Balance: {closing_balance}')
                    print('Buy Transaction:')
                    pprint(buy_txns)
                    print('Sell Transaction:')
                    pprint(sell_txns)
                else:
                    pass # All transactions of this investment have been captured.
            # if first_txn_date is None and txn_date is not None:
            #     first_txn_date = txn_date
            #     last_txn_date = txn_date
            # if txn_date is not None and txn_date > last_txn_date:
            #     last_txn_date = txn_date

            del lines[0]

    return buy_txns + sell_txns
    # return buy_txns, sell_txns, first_txn_date, last_txn_date, closing_balance

def pdf2json(user_id, pdf_file, pw):
    """
    Use 'text' string if passed, else use the text_file to get text string.
    parse cas text line by line and create Python data structure
    """
    # Read pdf and covert to text
    cas_text = pdf2txt(pdf_file, pw)
    # Save text file - optional
    # cas_text = save_cas_text_file(cas_text, CAS_TEXT_FILE)
    # Parse and extract investor name and transactions list from the text
    cas_text_lines = cas_text.splitlines()
    cas_from_date, cas_to_date = get_statement_dates(cas_text_lines)

    # Parse the CAS Text for first investment
    isin, folio, scheme_name, investor_name, pan = get_next_investment(cas_text_lines)
    investor_name = re.sub(r'\s+', ' ', investor_name).title() # Multiple spaces to single space
    investment_file_manager = InvestmentFileManager(user_id, investor_name)

    while isin:  # For the current found investment (isin is None, is not found)
        # Parse the CAS Text for transactions in the current found investment
        txns = parse_for_investment_txns(cas_text_lines, isin, folio)
        investment_file_manager.add_investment({
            "ISIN": isin,
            "Folio": folio,
            "SchemeName": scheme_name,
            "Transactions": txns,
        })
        # Parse the CAS Text for next investment
        isin, folio, scheme_name, investor_name, pan = get_next_investment(cas_text_lines)

    return 0

