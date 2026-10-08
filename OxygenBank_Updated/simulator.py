"""Projects the campus to 2050: business-as-usual vs an Oxygen Bank deposit policy."""
import math
from dataclasses import replace
import numpy as np
import pandas as pd
import config as C
from model import apply_transaction, compute_metrics


def fit_growth_rate(years, population) -> float:
    """Continuous growth rate from historical data (log-linear regression)."""
    return float(np.polyfit(years, np.log(population), 1)[0])


def simulate(start_state, start_year=2026, end_year=2050, r=0.05, capacity=20000,
             trees_per_year=0, solar_m2_per_year=0, green_roof_m2_per_year=0,
             rain_m2_per_year=0) -> pd.DataFrame:
    s = replace(start_state)
    p0 = s.population
    capacity = max(capacity, p0 * 1.01)

    def pop_at(t):  # logistic growth
        return capacity / (1 + ((capacity - p0) / p0) * math.exp(-r * t))

    cohorts, cum_cost, rows = [], 0.0, []
    for year in range(start_year, end_year + 1):
        t = year - start_year
        if t > 0:
            new_people = pop_at(t) - pop_at(t - 1)
            s = apply_transaction(s, "construction", new_people * C.BUILT_M2_PER_PERSON)

            # deposits (limited by available space)
            solar_q = min(solar_m2_per_year, s.roof_free_m2)
            s = apply_transaction(s, "solar_canopy", solar_q)
            roof_q = min(green_roof_m2_per_year, s.roof_free_m2)
            s = apply_transaction(s, "green_roof", roof_q)
            s = apply_transaction(s, "rainwater_harvest", rain_m2_per_year)
            tree_q = min(trees_per_year, s.plantable_m2 / C.SPACE_PER_TREE_M2)
            s = replace(s, plantable_m2=s.plantable_m2 - tree_q * C.SPACE_PER_TREE_M2)
            cohorts.append((year, tree_q))
            cum_cost += (solar_q * C.DEPOSITS["solar_canopy"]["cost"]
                         + roof_q * C.DEPOSITS["green_roof"]["cost"]
                         + rain_m2_per_year * C.DEPOSITS["rainwater_harvest"]["cost"]
                         + tree_q * C.DEPOSITS["plant_trees"]["cost"])

        # new trees only deliver benefits as they mature
        eff = sum(n * min(1.0, (year - y) / C.MATURITY_YEARS) for y, n in cohorts)
        view = replace(s, tree_carbon_kg=s.tree_carbon_kg + eff * C.CO2_PER_MATURE_TREE,
                       canopy_m2=s.canopy_m2 + eff * C.CANOPY_PER_MATURE_TREE)
        m = compute_metrics(view)
        rows.append({
            "year": year, "population": round(s.population), "energy_kwh": round(s.energy_kwh),
            "carbon_score": m["pillars"]["carbon"]["score"],
            "water_score": m["pillars"]["water"]["score"],
            "cooling_score": m["pillars"]["cooling"]["score"],
            "eco_score": m["eco_score"], "status": m["status"],
            "green_cover_pct": m["green_cover_pct"], "cum_cost_inr": cum_cost,
        })
    return pd.DataFrame(rows)


def first_overdraft_year(df):
    hit = df[df.eco_score < C.OVERDRAFT_BELOW]
    return int(hit.year.iloc[0]) if len(hit) else None
