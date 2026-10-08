"""Oxygen Bank ecological decision engine.

The live development model answers one practical question:
"Can this proposed development be made environmentally balanced, and what
interventions would improve it?"

Important: missing data is never silently treated as a perfect value.
"""
from dataclasses import dataclass, replace
import math
import pandas as pd
import config as C


@dataclass
class CampusState:
    total_area_m2: float
    tree_count: float
    tree_carbon_kg: float
    canopy_m2: float
    lawn_m2: float
    green_roof_m2: float
    shaded_m2: float
    solar_m2: float
    rain_catchment_m2: float
    energy_kwh: float
    population: float
    plantable_m2: float
    roof_free_m2: float


def load_baseline() -> CampusState:
    trees = pd.read_csv(C.TREES_CSV)
    return CampusState(
        tree_count=len(trees),
        tree_carbon_kg=float(trees.co2_kg_per_year.sum()),
        canopy_m2=float(trees.canopy_m2.sum()),
        **C.BASELINE,
    )


def apply_transaction(s: CampusState, category: str, qty: float) -> CampusState:
    """Return a new state after a ledger transaction."""
    qty = max(0.0, float(qty))
    if category == "plant_trees":
        return replace(
            s,
            tree_count=s.tree_count + qty,
            tree_carbon_kg=s.tree_carbon_kg + qty * C.CO2_PER_MATURE_TREE,
            canopy_m2=s.canopy_m2 + qty * C.CANOPY_PER_MATURE_TREE,
            plantable_m2=max(0, s.plantable_m2 - qty * C.SPACE_PER_TREE_M2),
        )
    if category == "green_roof":
        return replace(s, green_roof_m2=s.green_roof_m2 + qty,
                       roof_free_m2=max(0, s.roof_free_m2 - qty))
    if category == "solar_canopy":
        return replace(s, solar_m2=s.solar_m2 + qty,
                       roof_free_m2=max(0, s.roof_free_m2 - qty))
    if category == "rainwater_harvest":
        return replace(s, rain_catchment_m2=s.rain_catchment_m2 + qty)
    if category == "shaded_area":
        return replace(s, shaded_m2=s.shaded_m2 + qty,
                       plantable_m2=max(0, s.plantable_m2 - qty))
    if category == "tree_loss":
        n = min(qty, s.tree_count)
        avg_c = s.tree_carbon_kg / s.tree_count if s.tree_count else 0
        avg_can = s.canopy_m2 / s.tree_count if s.tree_count else 0
        return replace(s, tree_count=s.tree_count - n,
                       tree_carbon_kg=max(0, s.tree_carbon_kg - n * avg_c),
                       canopy_m2=max(0, s.canopy_m2 - n * avg_can))
    if category == "construction":
        green_loss = qty * C.GREEN_LOSS_FRACTION
        s = replace(
            s,
            energy_kwh=s.energy_kwh + qty * C.ENERGY_PER_BUILT_M2,
            population=s.population + qty / C.BUILT_M2_PER_PERSON,
            lawn_m2=max(0, s.lawn_m2 - green_loss),
            plantable_m2=max(0, s.plantable_m2 - green_loss),
        )
        return apply_transaction(s, "tree_loss", qty * C.TREES_LOST_PER_BUILT_M2)
    if category == "energy_increase":
        return replace(s, energy_kwh=s.energy_kwh + qty)
    if category == "population_increase":
        return replace(s, population=s.population + qty)
    raise ValueError(f"Unknown category: {category}")


def _pillar(value, target):
    score = min(100.0, 100.0 * value / target) if target > 0 else 0.0
    return {"value": value, "target": target, "score": score}


def compute_metrics(s: CampusState, rainfall_mm: float | None = None) -> dict:
    """Legacy ledger metrics, kept for the original Oxygen Bank pages."""
    harvest_l_per_m2 = (
        C.HARVEST_L_PER_M2 if rainfall_mm is None
        else max(0.0, float(rainfall_mm)) * C.RUNOFF_COEFF
    )
    emissions = s.energy_kwh * C.EMISSION_FACTOR + s.population * C.OTHER_KG_PER_PERSON
    offsets = (
        s.tree_carbon_kg
        + s.green_roof_m2 * C.GREEN_ROOF_CO2
        + s.solar_m2 * C.SOLAR_KWH_PER_M2 * C.EMISSION_FACTOR
    )
    water_demand = s.population * C.WATER_L_PER_PERSON_DAY * 365 / 1000
    harvest = s.rain_catchment_m2 * harvest_l_per_m2 / 1000
    green = s.lawn_m2 + s.green_roof_m2 + s.shaded_m2

    pillars = {
        "carbon": _pillar(offsets, C.CARBON_OFFSET_TARGET * emissions),
        "water": _pillar(harvest, C.WATER_HARVEST_TARGET * water_demand),
        "cooling": _pillar(green, C.GREEN_COVER_TARGET * s.total_area_m2),
    }
    score = sum(C.WEIGHTS[k] * pillars[k]["score"] for k in pillars)
    status = status_for_score(score)
    return {
        "pillars": pillars,
        "eco_score": score,
        "status": status,
        "emissions_kg": emissions,
        "offsets_kg": offsets,
        "water_demand_m3": water_demand,
        "green_cover_pct": 100 * green / s.total_area_m2 if s.total_area_m2 else 0,
    }


def status_for_score(score: float) -> str:
    if score >= C.HEALTHY_MIN:
        return "Balanced"
    if score >= C.TRANSITION_MIN:
        return "Transition"
    if score >= C.HIGH_PRESSURE_MIN:
        return "High Pressure"
    return "Ecological Stress"


def status_for_pillar(score: float) -> str:
    if score >= 75:
        return "Good"
    if score >= 60:
        return "Moderate"
    if score >= 40:
        return "High Pressure"
    return "Critical"


def _num(x, lo=0.0, hi=float("inf")):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return lo
    if not math.isfinite(v):
        return lo
    return min(hi, max(lo, v))


def _data(data, key, default=0.0):
    return _num(data.get(key, default))


def _core_values(data, intervention=None):
    """Calculate physical quantities for a development scenario."""
    intervention = intervention or {}

    total_area = max(_data(data, "total_area_m2"), 1.0)
    current_built = _data(data, "current_built_m2")
    proposed = _data(data, "proposed_construction_m2")
    current_pop = _data(data, "population")
    additional_pop = _data(data, "additional_population")
    trees = _data(data, "trees")
    green_initial = _data(data, "green_cover_m2")
    green_removed = _data(data, "green_area_removed_m2")

    current_water = _data(data, "current_annual_water_m3")
    additional_water = _data(data, "additional_water_demand_m3")
    current_electricity = _data(data, "annual_electricity_kwh")
    additional_electricity = _data(data, "additional_electricity_kwh")
    renewable = _data(data, "annual_renewable_kwh")
    current_reuse = _data(data, "reused_water_m3")
    current_rainwater = _data(data, "rainwater_harvested_m3")

    # If additional demand was not supplied, use conservative model estimates.
    if additional_water <= 0 and additional_pop > 0:
        additional_water = (
            additional_pop * C.WATER_L_PER_PERSON_DAY * 365 / 1000
        )

    if additional_electricity <= 0 and proposed > 0:
        additional_electricity = proposed * C.ENERGY_PER_BUILT_M2

    extra_trees = _data(intervention, "extra_trees")
    extra_green = _data(intervention, "extra_green_m2")
    extra_green_roof = _data(intervention, "extra_green_roof_m2")
    extra_shaded = _data(intervention, "extra_shaded_m2")
    extra_rainwater = _data(intervention, "extra_rainwater_m3")
    extra_reuse = _data(intervention, "extra_reuse_m3")
    extra_renewable = _data(intervention, "extra_renewable_kwh")

    population_after = current_pop + additional_pop
    built_after = current_built + proposed

    green_after = max(0.0, green_initial - green_removed + extra_green)
    trees_after = trees + extra_trees
    green_roof = extra_green_roof
    shaded = extra_shaded

    annual_water_demand = max(
        0.0,
        current_water + additional_water,
    )
    # If the user did not know current consumption, derive a transparent estimate.
    if current_water <= 0:
        annual_water_demand = (
            population_after * C.WATER_L_PER_PERSON_DAY * 365 / 1000
        )

    sustainable_water = (
        max(0.0, current_rainwater)
        + max(0.0, current_reuse)
        + extra_rainwater
        + extra_reuse
    )

    total_electricity = max(
        0.0,
        current_electricity + additional_electricity,
    )
    total_renewable = max(0.0, renewable + extra_renewable)
    grid_electricity = max(0.0, total_electricity - total_renewable)

    emissions = (
        grid_electricity * C.EMISSION_FACTOR
        + population_after * C.OTHER_KG_PER_PERSON
    )

    green_effective = green_after + green_roof + C.SHADE_GREEN_CREDIT * shaded
    green_pct = 100.0 * green_after / total_area
    tree_density_per_ha = trees_after / total_area * 10000.0

    return {
        "total_area": total_area,
        "built_after": built_after,
        "population_after": population_after,
        "green_after": green_after,
        "green_removed": green_removed,
        "trees_after": trees_after,
        "green_roof": green_roof,
        "shaded": shaded,
        "annual_water_demand": annual_water_demand,
        "sustainable_water": sustainable_water,
        "water_gap": max(0.0, annual_water_demand - sustainable_water),
        "total_electricity": total_electricity,
        "renewable_electricity": total_renewable,
        "grid_electricity": grid_electricity,
        "emissions_kg": emissions,
        "green_effective": green_effective,
        "green_pct": green_pct,
        "tree_density_per_ha": tree_density_per_ha,
    }


def _score_carbon(v):
    intensity = (
        v["emissions_kg"] / v["built_after"]
        if v["built_after"] > 0 else v["emissions_kg"]
    )
    # Prototype pressure benchmark, configurable in config.py.
    score = 100.0 if intensity <= C.CARBON_GOOD_INTENSITY_KG_M2 else 100.0 * max(0.0, 1.0 - (intensity - C.CARBON_GOOD_INTENSITY_KG_M2) / (C.CARBON_PRESSURE_LIMIT_KG_M2 - C.CARBON_GOOD_INTENSITY_KG_M2))
    renewable_share = (
        v["renewable_electricity"] / v["total_electricity"]
        if v["total_electricity"] > 0 else 0.0
    )
    score = min(100.0, score + renewable_share * C.RENEWABLE_SHARE_BONUS)
    return max(0.0, min(100.0, score)), intensity, renewable_share


def _score_water(v):
    demand = v["annual_water_demand"]
    if demand <= 0:
        return 100.0, 100.0, 0.0

    per_person = demand / max(v["population_after"], 1.0) / 365 * 1000
    efficiency_score = min(100.0, C.WATER_PER_PERSON_BENCHMARK_LPD / max(per_person, 0.1) * 100)
    coverage = 100.0 * v["sustainable_water"] / demand
    coverage_score = min(100.0, (coverage / 100.0) / C.WATER_COVERAGE_TARGET * 100.0)

    score = (
        C.WATER_EFFICIENCY_WEIGHT * efficiency_score
        + (1 - C.WATER_EFFICIENCY_WEIGHT) * coverage_score
    )
    return max(0.0, min(100.0, score)), per_person, coverage


def _score_cooling(v):
    green_score = min(100.0, v["green_pct"] / (C.GREEN_COVER_TARGET * 100) * 100)
    tree_score = min(100.0, v["tree_density_per_ha"] / C.TREE_DENSITY_TARGET_PER_HA * 100)
    score = C.GREEN_AREA_WEIGHT * green_score + C.TREE_DENSITY_WEIGHT * tree_score
    return max(0.0, min(100.0, score)), green_score, tree_score


def calculate_development_metrics(data: dict, intervention=None) -> dict:
    """Return a transparent development scenario: impact, scores and gaps."""
    v = _core_values(data, intervention)

    carbon_score, carbon_intensity, renewable_share = _score_carbon(v)
    water_score, water_per_person, water_coverage = _score_water(v)
    cooling_score, green_component, tree_component = _score_cooling(v)

    pillars = {
        "carbon": {
            "score": carbon_score,
            "status": status_for_pillar(carbon_score),
            "value": v["emissions_kg"],
            "target": C.CARBON_GOOD_INTENSITY_KG_M2,
        },
        "water": {
            "score": water_score,
            "status": status_for_pillar(water_score),
            "value": v["sustainable_water"],
            "target": v["annual_water_demand"] * C.WATER_COVERAGE_TARGET,
        },
        "cooling": {
            "score": cooling_score,
            "status": status_for_pillar(cooling_score),
            "value": v["green_effective"],
            "target": v["total_area"] * C.GREEN_COVER_TARGET,
        },
    }

    eco = sum(C.WEIGHTS[k] * pillars[k]["score"] for k in C.WEIGHTS)

    return {
        "pillars": pillars,
        "eco_score": max(0.0, min(100.0, eco)),
        "status": status_for_score(eco),
        "state": scenario_state(data, intervention),
        "impact": {
            "built_after_m2": v["built_after"],
            "built_increase_pct": 100 * _data(data, "proposed_construction_m2") / max(_data(data, "total_area_m2"), 1.0),
            "population_after": v["population_after"],
            "green_after_m2": v["green_after"],
            "green_pct": v["green_pct"],
            "green_loss_m2": v["green_removed"],
            "trees_after": v["trees_after"],
            "annual_water_demand_m3": v["annual_water_demand"],
            "sustainable_water_m3": v["sustainable_water"],
            "water_gap_m3": v["water_gap"],
            "water_coverage_pct": water_coverage,
            "water_per_person_lpd": water_per_person,
            "electricity_kwh": v["total_electricity"],
            "renewable_kwh": v["renewable_electricity"],
            "renewable_share_pct": renewable_share * 100,
            "grid_electricity_kwh": v["grid_electricity"],
            "emissions_kg": v["emissions_kg"],
            "emissions_t": v["emissions_kg"] / 1000,
            "carbon_intensity_kg_m2": carbon_intensity,
            "tree_density_per_ha": v["tree_density_per_ha"],
        },
    }


def scenario_state(data: dict, intervention=None) -> CampusState:
    """Build a CampusState for compatibility with existing app pages."""
    v = _core_values(data, intervention)
    return CampusState(
        total_area_m2=v["total_area"],
        tree_count=v["trees_after"],
        tree_carbon_kg=v["trees_after"] * C.CO2_PER_MATURE_TREE,
        canopy_m2=v["trees_after"] * C.CANOPY_PER_MATURE_TREE,
        lawn_m2=v["green_after"],
        green_roof_m2=v["green_roof"],
        shaded_m2=v["shaded"],
        solar_m2=0.0,
        rain_catchment_m2=0.0,
        energy_kwh=v["total_electricity"],
        population=v["population_after"],
        plantable_m2=max(0.0, v["total_area"] - v["built_after"] - v["green_after"]),
        roof_free_m2=max(0.0, v["built_after"] - v["green_roof"]),
    )


def _intervention_text(pillar):
    return {
        "carbon": [
            "Add renewable generation to reduce grid electricity.",
            "Reduce building energy demand through efficient cooling, lighting and equipment.",
            "Prioritise low-carbon construction and operations.",
        ],
        "water": [
            "Increase rainwater harvesting/storage.",
            "Add treated-water reuse for irrigation and other non-potable demand.",
            "Reduce demand with efficient fixtures and irrigation controls.",
        ],
        "cooling": [
            "Restore green area lost to construction.",
            "Add canopy trees and shaded pedestrian areas.",
            "Use green roofs where ground area cannot be restored.",
        ],
    }[pillar]


def recommendations(data: dict, bau=None) -> dict:
    """Generate a simple, transparent intervention plan."""
    bau = bau or calculate_development_metrics(data)
    scores = {k: bau["pillars"][k]["score"] for k in C.WEIGHTS}
    ranked = sorted(scores, key=scores.get)

    plan = []
    # Quantities are deliberately transparent rather than pretending to be an optimizer.
    water_gap = bau["impact"]["water_gap_m3"]
    if scores["water"] < C.RECOMMENDATION_TRIGGER:
        target = bau["impact"]["annual_water_demand_m3"] * C.WATER_COVERAGE_TARGET
        extra_needed = max(0.0, target - bau["impact"]["sustainable_water_m3"])
        if extra_needed > 0:
            plan.append({
                "pillar": "water",
                "action": "Increase rainwater harvesting / water reuse",
                "quantity": extra_needed,
                "unit": "m³/year sustainable supply",
                "reason": f"Current sustainable supply is {bau['impact']['water_coverage_pct']:.0f}% of demand.",
            })

    if scores["cooling"] < C.RECOMMENDATION_TRIGGER:
        green_target = bau["impact"]["built_after_m2"] * 0.0 + bau["impact"]["built_after_m2"]
        required_green = bau["impact"]["green_after_m2"]
        target_area = bau["impact"]["built_after_m2"] * 0.0 + _data(data, "total_area_m2") * C.GREEN_COVER_TARGET
        extra_green = max(0.0, target_area - required_green)
        if extra_green > 0:
            plan.append({
                "pillar": "cooling",
                "action": "Restore/add green and cooling area",
                "quantity": extra_green,
                "unit": "m²",
                "reason": f"Green cover is {bau['impact']['green_pct']:.1f}% versus the {C.GREEN_COVER_TARGET*100:.0f}% prototype target.",
            })

    if scores["carbon"] < C.RECOMMENDATION_TRIGGER:
        current_grid = bau["impact"]["grid_electricity_kwh"]
        target_grid = current_grid * (1 - C.RENEWABLE_RECOMMENDATION_TARGET)
        extra_renewable = max(0.0, current_grid - target_grid)
        plan.append({
            "pillar": "carbon",
            "action": "Add renewable electricity / energy-efficiency measures",
            "quantity": extra_renewable,
            "unit": "kWh/year renewable generation or avoided demand",
            "reason": f"Carbon intensity is {bau['impact']['carbon_intensity_kg_m2']:.1f} kg CO₂e/m²/year.",
        })

    return {
        "weakest_pillar": ranked[0],
        "plan": plan,
        "explanation": _intervention_text(ranked[0]),
    }


def calculate_live_metrics(data: dict, apply_proposed: bool = True) -> dict:
    """Compatibility wrapper used by app.py."""
    # The live dashboard intentionally includes the proposed development as BAU.
    # For the 'before' scenario use apply_proposed=False.
    d = dict(data)
    if not apply_proposed:
        d["proposed_construction_m2"] = 0.0
        d["additional_population"] = 0.0
        d["additional_water_demand_m3"] = 0.0
        d["additional_electricity_kwh"] = 0.0
        d["green_area_removed_m2"] = 0.0

    return calculate_development_metrics(d)
