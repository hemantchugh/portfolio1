from pathlib import Path

from model.investor import Investor
from model.mf_master import MFSchemeMaster
import model.investment_file as investment_files

class User:
    def __init__(self, id, project_folder=""):
        self.user_id = id
        self.datafolder = Path("data") / self.user_id
        self.mf_master = MFSchemeMaster(self.user_id)   # Instantiated only once for a user
        self.investors = self.load_all_investors()
        user_data_folder = f"data\\{id}"
        Path(user_data_folder).mkdir(parents=True, exist_ok=True)


    def load_all_investors(self):
        # Fetch all available investors for this user from investments JSON files
        investors = {}
        investor_names = investment_files.get_all_investor_names(self.user_id)
        for investor_name in investor_names:
            print(f"Loading started for investor: {investor_name}... ",)
            investors[investor_name] = Investor(self, investor_name)
            print(f"Done loading data for investor: {investor_name}!")

        return investors

    def get_investor(self, investor_name):
        return self.investors[investor_name]

    @property
    def tags(self):
        # tags = list(investor.get_tags() for investor in self.investors.values())
        list_of_tags = [investor.tags for investor in self.investors.values()]
        unique_tags = list({tag for tags in list_of_tags for tag in tags})
        return unique_tags

    @property
    def compiled_tags(self):
        # Combine compiled tags dictionaries from all investors
        combined = {}
        for investor in self.investors.values():
            for cat, subs in investor.compiled_tags.items():
                combined.setdefault(cat, set())  # Ensure the category exists (always)
                if subs:     # Add subcategories if any
                    combined[cat].update(subs)

        combined = {cat: sorted(list(subs)) for cat, subs in combined.items()}
        return combined

    def __iter__(self):
        return iter(self.investors.values())


def get_all_user_ids():
    # All subfolder names in the "data" folder except "common" subfolder
    data_folder_path = Path("data")
    subfolders = [f.name for f in data_folder_path.iterdir() if f.is_dir() and f.name != "common"]
    return subfolders


if __name__ == '__main__':
    for investor in User("hemant", ".."):
        print(investor.name)

