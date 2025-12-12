import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
import pandas as pd

@dataclass
class MFScheme:
    """Dataclass representing a Mutual Fund Scheme record."""
    isin: str
    scheme_name: str
    last_txn_date: str      # Used for sorting the schemes for maintenance view
    is_under_ltcg: Optional[bool] = False
    is_under_stcg: Optional[bool] = False
    is_under_asr: Optional[bool] = False
    exit_load_days: Optional[int] = None
    ltcg_days: Optional[int] = None
    tags: List[str] = field(default_factory=list)


class MFSchemeMaster:
    """
    Class to manage Mutual Fund Scheme master data stored in a JSON file.
    Handles automatic persistence, validation, and structured data access.
    """
    LTCG_AFTER_STCG_DAYS = 365
    LTCG_AFTER_ASR_DAYS = 365 * 2

    _instances: Dict[str, "MFSchemeMaster"] = {}  # one instance per user_id
    # VALID_TAX_TREATMENTS = {"ST/LTCG", "ASR/LTCG", "ASR Only"}

    def __new__(cls, user_id: str):
        if user_id not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[user_id] = instance
        return cls._instances[user_id]

    def __init__(self, user_id: str):
        """
        Initialize the manager for a given user.
        The data file is automatically created under: data/<user_id>/mf_master.json
        """
        self.user_id = user_id
        self.filepath = Path("data") / user_id / "mf_master.json"
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

        if not self.filepath.exists():
            self.filepath.write_text("{}", encoding="utf-8")

        self.schemes: Dict[str, MFScheme] = self._load()

    # ---------- Core File Operations ----------

    def _load(self) -> Dict[str, MFScheme]:
        """Load data from JSON and return dictionary of MFScheme objects."""
        with open(self.filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {isin: MFScheme(**record) for isin, record in data.items()}

    def _save(self):
        """Persist all scheme records to JSON file."""
        data = {isin: asdict(self._set_derived_data(scheme)) for isin, scheme in self.schemes.items()}
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ---------- Validation ----------

    def _validate(self, scheme: MFScheme):
        """Validate fields of the given MFScheme object."""
        if not scheme.isin or not isinstance(scheme.isin, str):
            raise ValueError("ISIN must be a non-empty string.")
        if not scheme.scheme_name or not isinstance(scheme.scheme_name, str):
            raise ValueError("Scheme name must be a non-empty string.")
        if scheme.exit_load_days is not None and scheme.exit_load_days < 0:
            raise ValueError("Exit load days must be 0 or a positive integer.")
        if scheme.ltcg_days is not None and scheme.ltcg_days < 0:
            raise ValueError("LTCG applicable days must be None or positive integer.")
        # if scheme.tax_treatment and scheme.tax_treatment not in self.VALID_TAX_TREATMENTS:
        #     raise ValueError(f"Invalid tax treatment: {scheme.tax_treatment}")
        if not all(isinstance(tag, str) and tag.strip() for tag in scheme.tags):
            raise ValueError("All tags must be non-empty strings.")
        return self

    def _set_derived_data(self, scheme: MFScheme):
        # Derived value for STCG Tax --> When LTCG is applicable but ASR is Not applicable
        if scheme.is_under_ltcg and scheme.is_under_asr == False:
            scheme.is_under_stcg = True
        # Derived LTCG Start Days --> LTCG is applicable but days are not set -->
        # When ASR is applicable then 730 days, else (when STCG is applicable) then 365 days
        # if scheme.ltcg_days is None and scheme.is_under_ltcg:
        scheme.ltcg_days = 99999
        if scheme.is_under_ltcg and scheme.is_under_stcg:
            scheme.ltcg_days = self.LTCG_AFTER_STCG_DAYS
        if scheme.is_under_ltcg and scheme.is_under_asr:
            scheme.ltcg_days = self.LTCG_AFTER_ASR_DAYS
        return scheme

    # ---------- CRUD Operations ----------
    def exists(self, isin: str) -> bool:
        """Check if a scheme exists."""
        return isin in self.schemes

    def add_scheme(self, isin: str, scheme_name: str, last_txn_date: str, ignore_if_exists: bool= True):
        """
        Add a new MF Scheme with minimal fields.
        Other fields default to None or empty list.
        Automatically saves to file.
        """
        if isin in self.schemes:
            if ignore_if_exists:
                return
            else:
                raise ValueError(f"Scheme with ISIN {isin} already exists.")
        new_scheme = MFScheme(isin=isin, scheme_name=scheme_name, last_txn_date=last_txn_date)
        self._validate(new_scheme)
        self._set_derived_data(new_scheme)
        self.schemes[isin] = new_scheme

        self._save()
        return self

    def save_from_df(self, df: pd.DataFrame):
        schemes = {}
        for _, row in df.iterrows():
            tags = []
            for tag in row["tags"]:
                tag = tag.strip()
                if not tag:
                    continue
                parts = [p.strip().title() for p in tag.split('/', 1)]  # handle at most one "/"
                tags.append('/'.join(parts))

            scheme = MFScheme(
                isin=row["isin"],
                scheme_name=row["scheme_name"],
                is_under_ltcg=row["is_under_ltcg"],
                is_under_asr=row["is_under_asr"],
                # tax_treatment=row["tax_treatment"],
                exit_load_days=row["exit_load_days"],
                # ltcg_days=row["ltcg_days"],
                tags=tags,
                last_txn_date=row["last_txn_date"],
              )
            self._set_derived_data(scheme)
            schemes[scheme.isin] = scheme
        self.schemes = schemes
        self._save()
        # print("Schemes Dataframe Saved.", datetime.now())
        return self


    def update_scheme(self, isin: str, **updates) -> None:
        """
        Update existing MF Scheme partially.
        Only provided fields are modified.
        Replaces 'tags' entirely (case-insensitive).
        Automatically saves to file.
        """
        if isin not in self.schemes:
            raise KeyError(f"No scheme found with ISIN {isin}")

        scheme = self.schemes[isin]

        for field_name, value in updates.items():
            if field_name == "tags" and isinstance(value, list):
                # Normalize tags to lower case and remove duplicates
                cleaned_tags = sorted(set(tag.strip().lower() for tag in value if tag.strip()))
                setattr(scheme, "tags", cleaned_tags)
            elif hasattr(scheme, field_name):
                setattr(scheme, field_name, value)
            else:
                raise ValueError(f"Invalid field: {field_name}")

        self._validate(scheme)
        self._save()

    def get_scheme(self, isin: str) -> Optional[MFScheme]:
        """
        Return a single scheme object for the given ISIN.
        Returns None if not found.
        """
        return self.schemes.get(isin)

    def get_schemes(self, isins: List[str]) -> Dict[str, MFScheme]:
        """
        Return a dictionary of {isin: MFScheme} for the given list of ISINs.
        Skips ISINs that are not found.
        """
        return {isin: self.schemes[isin] for isin in isins if isin in self.schemes}

    def get_all_schemes(self) -> List[MFScheme]:
        """Return all schemes currently loaded."""
        return list(self.schemes.values())

