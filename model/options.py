import json
from pathlib import Path
import copy
import datetime

import utils.utils as utils

ZERO_BALANCE_OPTIONS = [
    {
        "hide_before_date": datetime.date.today(),
        "selection_text": "Exclude zero balance",
        "display_text": "Excluded zero balance investments",
    },
    {
        "hide_before_date": utils.previous_fy_start_date(-1),
        "selection_text": "Include for current FY",
        "display_text": "Included investments sold out in current FY",
    },
    {
        "hide_before_date": utils.previous_fy_start_date(-2),
        "selection_text": "Include for previous FY",
        "display_text": "Included investments sold out in previous FY",
    },
    {
        "hide_before_date": None,
        "selection_text": "Include all investments",
        "display_text": "Included all zero balance investments",
    },
]

class Options:
    DEFAULTS = {
        "selected_investors_names": [],
        "selected_investor_name": "",
        "selected_hide_before_date": datetime.date.today(),  # "today"
        "selected_fy": utils.current_fy(),
        "selected_cats": [],
        "selected_subs": {},
    }

    def __init__(self, folder_path=""):
        self._filepath = Path(folder_path) / "options.json"
        self._options = self._load()
        self._original = copy.deepcopy(self._options)

    def _encode_json(self, obj):
        """Custom encoder: convert datetime.date to ISO string."""
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        return obj

    def _decode_json(self, obj):
        """Custom decoder: convert ISO strings back to datetime.date where needed."""
        # json doesn't support python dates, therefore all this taam-jhaam to save and retrieve dates
        # between json and python
        decoded = {}
        for key, value in obj.items():
            if key in self.DEFAULTS and isinstance(self.DEFAULTS[key], datetime.date):
                try:
                    decoded[key] = datetime.date.fromisoformat(value)
                except Exception:
                    decoded[key] = self.DEFAULTS[key]
            else:
                decoded[key] = value
        return decoded

    def _load(self):
        """Load options from JSON file, merge with defaults."""
        if self._filepath.exists():
            try:
                with open(self._filepath, "r") as f:
                    data = json.load(f)
                    data = self._decode_json(data)  # convert date field from iso (str) format to python date.
                    return {**self.DEFAULTS, **data}
            except (json.JSONDecodeError, OSError):
                print("⚠️  Warning: Options file corrupted. Resetting to defaults.")
        return copy.deepcopy(self.DEFAULTS)  # deepcopy to avoid modifying the default values

    def save(self):
        """Write current options to JSON file."""
        try:
            with open(self._filepath, "w") as f:
                json.dump(self._options, f, indent=4, default=self._encode_json)
            self._original = copy.deepcopy(self._options)
        except OSError as e:
            print(f"❌ Failed to save options: {e}")

    def discard_changes(self):
        """Revert to last saved version."""
        self._options = copy.deepcopy(self._original)

    def get(self, key, default=None):
        """Get single option."""
        return copy.deepcopy(self._options.get(key, default))

    def __getattr__(self, name):
        # print("Getting value for", name)
        # if name == "options":
        #     return self
        # else:
        return self._options.get(name)
            # return copy.deepcopy(self._options.get(name))

    def set(self, key, value):
        """Set single option (not auto-saved)."""
        self._options[key] = value

    def __setattr__(self, name, value):
        if name == "options" or name.startswith("_"):
            super().__setattr__(name, value)
        else:
            self._options[name] = value

    def get_all(self):
        """Return all options."""
        return copy.deepcopy(self._options)

    def set_all(self, new_options):
        """Bulk update."""
        if not isinstance(new_options, dict):
            raise ValueError("Expected a dict for new options.")
        self._options.update(new_options)

    def has_unsaved_changes(self):
        """Check if unsaved changes exist."""
        return self._options != self._original

    def reset(self):
        """Reset to defaults."""
        self._options = copy.deepcopy(self.DEFAULTS)

# Example usage
if __name__ == "__main__":
    opts = Options()

    print("Last backup date:", opts.get("last_backup_date"))

    # Update date
    opts.set("last_backup_date", datetime.date.today())

    print("Updated:", opts.get("last_backup_date"))
    print("Unsaved changes?", opts.has_unsaved_changes())

    opts.save()
