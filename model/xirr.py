from pyxirr import xirr as pyxirr
import pandas as pd

def cagr(buy_value, sell_value, buy_date, sell_date):
    years_held = (sell_date - buy_date).days / 365
    return (sell_value / buy_value) ** (1 / years_held) - 1

def xirr(investments, realized=False, unrealized=False, fy=None):
    investments = investments if isinstance(investments, list) else [investments]
    total = not (realized or unrealized)
    cashflows = []
    for inv in investments:
        if (realized or total): # and len(inv.mat) > 0:
            # Compute Realized xirr or total_xirr only if there are any Sell txns (else we get error)
            _add_realized_cashflows(inv, cashflows, fy)
        if (unrealized or total) and inv.holding > 0:
            # Compute UnRealized xirr or total_xirr only if there are any Unsold units available
            _add_unrealized_cashflows(inv, cashflows)
    cashflows_df = pd.DataFrame(data=cashflows, columns=["Date", "Value"])
    return 0 if len(cashflows_df) == 0 else pyxirr(cashflows_df)

def _add_realized_cashflows(investment, cashflows, fy=None):
    # for txn in investment.buy_txns:
    #     # Purchases are money out - so should be negative
    #     cashflows.append((txn.txn_date, txn.price * -1 * txn.sold_units))
    # for txn in investment.sell_txns:
    #     # sales are money in - so should be positive (units in sell_txn are already negative, therefor (* -1)
    #     if fy is None or fy == txn.fy:
    #         cashflows.append((txn.txn_date, txn.price * txn.units * -1))
    for txn in investment.matched_txns:
        if fy is None or fy == txn.fy:
            cashflows.append((txn.buy_txn.txn_date, txn.buy_amount * -1))
            cashflows.append((txn.sell_txn.txn_date, txn.sell_amount))

def _add_unrealized_cashflows(investment, cashflows):
    for txn in investment.buy_txns:
        cashflows.append((txn.txn_date, txn.price * -1 * txn.unsold_units))
    cashflows.append((investment.nav_date, investment.nav * investment.holding))

