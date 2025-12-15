import json
import os
from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any, List, Optional
from pathlib import Path


@dataclass
class Transaction:
    """Represents a single buy or sell transaction for an investment."""
    date: str  # Format: YYYY-MM-DD
    type: str  # "buy" or "sell"
    quantity: int
    price: float
    tax: float
    source: str

    def __post_init__(self):
        """Validate transaction fields after initialization."""
        try:
            datetime.strptime(self.date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid date format: {self.date}, expected YYYY-MM-DD")
        if self.type not in {"buy", "sell"}:
            raise ValueError(f"Transaction type must be 'buy' or 'sell', got: {self.type}")
        # if self.quantity <= 0:
        #     raise ValueError("Quantity must be a positive integer")
        if self.price <= 0:
            raise ValueError("Price must be a positive number")


@dataclass
class Investment:
    """Represents an investment identified by ISIN and Folio."""
    ISIN: str
    Folio: str
    SchemeName: str
    Transactions: list[Transaction] = field(default_factory=list)


class InvestmentFileManager:
    """
    Manages investment records stored in a JSON file.
    Supports CRUD operations, summary calculations, and transaction management.
    """

    def __init__(self, user_id: str, investor_name: str):
        """
        Initialize the InvestmentManager.

        Args:
            investor_name: Path to the JSON file to store/load investments.
        """
        # self.filepath = f'data\\{user_id}\\{investor_name.lower().replace(' ', '_')}_investments.json'
        self.user_id = user_id
        self.filepath = Path("data") / user_id / f"{investor_name.lower().replace(' ', '_')}_investments.json"
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

        self.investments: list[Investment] = []
        self.investor_name = investor_name
        self._load()

    def _load(self) -> None:
        """Load investment data from JSON file if it exists, else initialize empty list."""
        if os.path.exists(self.filepath):
            with open(self.filepath, "r", encoding="utf-8") as f:
                try:
                    raw = json.load(f)
                    self.investments = [
                        Investment(
                            ISIN=rec["ISIN"],
                            Folio=rec["Folio"],
                            SchemeName=rec["SchemeName"],
                            Transactions=[Transaction(**txn) for txn in rec["Transactions"]],
                        )
                        for rec in raw
                    ]

                except json.JSONDecodeError:
                    self.investments = []
        else:
            self.investments = []


    def save(self) -> None:
        """
        Save the current investment data to the JSON file.
        Can be used to manually persist changes.
        """
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump([asdict(inv) for inv in self.investments], f, indent=4)
        # print(self.filepath, "saved")

    def _save(self) -> None:
        """Auto-save wrapper called internally after every change."""
        self.save()

    def _find_investment(self, isin: str, folio: str) -> Optional[Investment]:
        """
        Find an investment by ISIN and Folio.

        Args:
            isin: The ISIN of the investment.
            folio: The Folio of the investment.

        Returns:
            Investment object if found, else None.
        """
        for inv in self.investments:
            if inv.ISIN == isin and inv.Folio == folio:
                return inv
        return None

    def add_investment(self, record: dict[str, Any], allow_same_date=False) -> None:
        """
        Add a new investment or append transactions if investment already exists.
        Transactions are validated and sorted by date.

        Args:
            record: Dictionary containing investment data, e.g.,
                {
                    "ISIN": str,
                    "Folio": str,
                    "SchemeName": str,
                    "Transactions": [ {date, type, quantity, price}, ... ]
                }

        Raises:
            ValueError: If required fields are missing or transactions are invalid.
        """
        isin, folio = record.get("ISIN"), record.get("Folio")
        if not isin or not folio:
            raise ValueError("ISIN and Folio are required")
        scheme_name = record.get("SchemeName", "")
        transactions_raw = record.get("Transactions", [])  # txns => List of structures
        transactions = [Transaction(**txn) for txn in transactions_raw] # Converted to list of data class

        # This is added on 10-10-2025 as a precautionary measure (Remove if any issue)
        transactions.sort(key=lambda t: t.date)

        existing_investment = self._find_investment(isin, folio)
        if existing_investment:
            # Add only transactions with new dates
            existing_dates = {txn.date for txn in existing_investment.Transactions}
            if allow_same_date:
                # All given transactions to be considered as new txns
                new_txns = transactions
            else:
                # Add transactions only dates which are not already in the investment
                new_txns = [txn for txn in transactions if txn.date not in existing_dates]
            if new_txns:
                # existing_investment.Transactions.extend(transactions)
                existing_investment.Transactions.extend(new_txns)
                existing_investment.Transactions.sort(key=lambda t: t.date)
        else:
            new_inv = Investment(ISIN=isin, Folio=folio, SchemeName=scheme_name, Transactions=transactions)
            self.investments.append(new_inv)

        self._save()

    def get_investment(self, isin: str, folio: str) -> Optional[Investment]:
        """
        Retrieve an investment by ISIN and Folio.

        Args:
            isin: The ISIN of the investment.
            folio: The Folio of the investment.

        Returns:
            Investment object if found, else None.
        """
        return self._find_investment(isin, folio)

    def delete_investment(self, isin: str, folio: str) -> bool:
        """
        Delete an investment record by ISIN and Folio.

        Args:
            isin: The ISIN of the investment.
            folio: The Folio of the investment.

        Returns:
            True if deleted successfully, False if not found.
        """
        for i, inv in enumerate(self.investments):
            if inv.ISIN == isin and inv.Folio == folio:
                del self.investments[i]
                self._save()
                return True
        return False

    def update_scheme_name(self, isin: str, folio: str, new_name: str) -> bool:
        """
        Update the scheme name of an investment.

        Args:
            isin: The ISIN of the investment.
            folio: The Folio of the investment.
            new_name: New scheme name to set.

        Returns:
            True if updated successfully, False if investment not found.
        """
        inv = self._find_investment(isin, folio)
        if inv:
            inv.SchemeName = new_name
            self._save()
            return True
        return False

    def list_investments(self) -> list[Investment]:
        """
        List all investments currently stored.

        Returns:
            List of Investment objects.
        """
        return self.investments

    def export_transactions(self, isin: str, folio: str) -> list[Transaction]:
        """
        Export all transactions for a given investment.

        Args:
            isin: The ISIN of the investment.
            folio: The Folio of the investment.

        Returns:
            List of Transaction objects, empty list if investment not found.
        """
        inv = self._find_investment(isin, folio)
        return inv.Transactions if inv else []

    # ----------- Summary Methods -----------

    def get_total_quantity(self, isin: str, folio: str) -> int:
        """
        Compute net holdings for an investment (buys minus sells).

        Args:
            isin: The ISIN of the investment.
            folio: The Folio of the investment.

        Returns:
            Net quantity (int), 0 if investment not found.
        """
        inv = self._find_investment(isin, folio)
        if not inv:
            return 0
        return sum(t.quantity if t.type == "buy" else -t.quantity for t in inv.Transactions)

    def get_total_invested(self, isin: str, folio: str) -> float:
        """
        Compute total invested amount for an investment (only buys considered).

        Args:
            isin: The ISIN of the investment.
            folio: The Folio of the investment.

        Returns:
            Total invested amount as float, 0.0 if investment not found.
        """
        inv = self._find_investment(isin, folio)
        if not inv:
            return 0.0
        return sum(t.quantity * t.price for t in inv.Transactions if t.type == "buy")

    def get_average_buy_price(self, isin: str, folio: str) -> float:
        """
        Compute weighted average buy price (ignores sells).

        Args:
            isin: The ISIN of the investment.
            folio: The Folio of the investment.

        Returns:
            Average buy price as float, 0.0 if no buys or investment not found.
        """
        inv = self._find_investment(isin, folio)

import streamlit as st
def get_all_investor_names(user_id: str) -> list[str]:
    # st.write("CWD:", os.getcwd())
    # st.write("Error reading here:", os.listdir("."))
    BASE_DIR = Path(__file__).parent
    datafolder = BASE_DIR / "data" / user_id
    filenames = [filename for filename in os.listdir(datafolder) if filename.endswith("_investments.json")]
    return [filename.replace("_investments.json", "").replace("_", " ").title() for filename in filenames]

def get_all(user_id: str) -> list[InvestmentFileManager]:
    investor_names = get_all_investor_names(user_id)
    return [InvestmentFileManager(user_id, investor_name) for investor_name in investor_names]

def get_one(user_id: str, investor_name: str) -> InvestmentFileManager:
    return InvestmentFileManager(user_id, investor_name)

if __name__ == "__main__":
    print(get_all_investor_names("hemant"))
