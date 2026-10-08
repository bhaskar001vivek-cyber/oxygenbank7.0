"""Generates synthetic campus data. Replace with real surveys/GIS data later."""
import numpy as np
import pandas as pd
import config as C

SPECIES = ["Neem", "Peepal", "Banyan", "Ashoka", "Mango", "Gulmohar", "Arjun", "Jamun"]


def generate(seed=42, n_trees=1200):
    rng = np.random.default_rng(seed)
    age = rng.integers(1, 31, n_trees)
    trees = pd.DataFrame({
        "tree_id": range(1, n_trees + 1),
        "species": rng.choice(SPECIES, n_trees),
        "age_years": age,
        "lat": C.CAMPUS_CENTER[0] + rng.normal(0, 0.0018, n_trees),
        "lon": C.CAMPUS_CENTER[1] + rng.normal(0, 0.0018, n_trees),
        "co2_kg_per_year": np.minimum(C.CO2_PER_MATURE_TREE, 3 + 1.4 * age),
        "canopy_m2": np.minimum(C.CANOPY_PER_MATURE_TREE, 2 + 1.2 * age),
    })
    trees.to_csv(C.TREES_CSV, index=False)

    years = np.arange(2016, 2027)
    pop = 4000 * np.exp(-0.05 * (2026 - years)) * rng.normal(1, 0.015, len(years))
    pd.DataFrame({"year": years, "population": pop.round()}).to_csv(C.POP_CSV, index=False)


if __name__ == "__main__":
    generate()
    print("Data generated in", C.DATA_DIR)
