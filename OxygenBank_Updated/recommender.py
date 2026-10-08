"""
Oxygen Bank - Recommendation engine.

This module is intentionally separate from app.py.

It provides:
    recommend(state, target, max_trees, max_rain)

The recommender evaluates deposit actions from config.DEPOSITS,
applies them through model.apply_transaction(), and chooses a
low-cost sequence that attempts to reach the requested Eco-Balance
score.
"""

from __future__ import annotations

import copy
import math
from typing import Any, Dict, List, Optional, Tuple

import config as C
import model


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _deposit_definitions() -> Dict[str, Dict[str, Any]]:
    """Return the configured deposit categories."""
    deposits = getattr(C, "DEPOSITS", None)

    if not isinstance(deposits, dict):
        return {}

    return deposits


def _get_number(
    data: Dict[str, Any],
    keys: Tuple[str, ...],
    default: Optional[float] = None,
) -> Optional[float]:
    """Get the first numeric value from a dictionary."""
    for key in keys:
        if key not in data:
            continue

        value = data[key]

        try:
            value = float(value)
        except (TypeError, ValueError):
            continue

        if math.isfinite(value):
            return value

    return default


def _label(category: str, definition: Dict[str, Any]) -> str:
    """Human-readable label for a deposit category."""
    for key in ("label", "name", "description"):
        value = definition.get(key)
        if value:
            return str(value)

    return str(category).replace("_", " ").title()


def _unit_cost(category: str, definition: Dict[str, Any]) -> float:
    """
    Extract the configured cost for one unit.

    Different versions of the project have used slightly different
    names, so support the common possibilities.
    """
    value = _get_number(
        definition,
        (
            "cost_inr",
            "cost",
            "unit_cost",
            "price",
            "cost_per_unit",
            "price_inr",
            "inr",
        ),
        None,
    )

    if value is None:
        raise ValueError(
            f"Deposit category '{category}' has no recognised cost field. "
            f"Add one of: cost_inr, cost, unit_cost, price, "
            f"cost_per_unit, price_inr."
        )

    return max(0.0, value)


def _unit_size(definition: Dict[str, Any]) -> float:
    """
    Quantity represented by one transaction unit.

    Most Oxygen Bank configurations use one unit = one item/m².
    """
    value = _get_number(
        definition,
        (
            "unit_size",
            "quantity_per_unit",
            "unit_quantity",
            "size",
        ),
        1.0,
    )

    return max(value, 1e-9)


def _is_tree_category(category: str, definition: Dict[str, Any]) -> bool:
    """Identify tree-related deposits."""
    text = " ".join(
        [
            str(category),
            str(definition.get("label", "")),
            str(definition.get("name", "")),
        ]
    ).lower()

    return any(
        word in text
        for word in (
            "tree",
            "trees",
            "plant",
            "planting",
            "sapling",
        )
    )


def _is_rain_category(category: str, definition: Dict[str, Any]) -> bool:
    """Identify rainwater-catchment deposits."""
    text = " ".join(
        [
            str(category),
            str(definition.get("label", "")),
            str(definition.get("name", "")),
        ]
    ).lower()

    return any(
        word in text
        for word in (
            "rain",
            "rainwater",
            "catchment",
            "water harvesting",
            "harvesting",
        )
    )


def _copy_state(state: Any) -> Any:
    """Make a safe copy of the model state."""
    try:
        return copy.deepcopy(state)
    except Exception:
        return copy.copy(state)


# ---------------------------------------------------------------------
# Model integration
# ---------------------------------------------------------------------

def _apply_deposit(
    state: Any,
    category: str,
    quantity: float,
) -> Any:
    """
    Apply a deposit using model.apply_transaction().

    The project has used slightly different signatures during
    development, so this adapter supports the common forms.
    """

    quantity = float(quantity)

    # Most likely signature:
    # apply_transaction(state, kind, category, quantity)
    attempts = [
        lambda: model.apply_transaction(
            state,
            "deposit",
            category,
            quantity,
        ),
        # Alternative:
        # apply_transaction(state, category, quantity, "deposit")
        lambda: model.apply_transaction(
            state,
            category,
            quantity,
            "deposit",
        ),
        # Alternative keyword form.
        lambda: model.apply_transaction(
            state=state,
            kind="deposit",
            category=category,
            quantity=quantity,
        ),
        # Alternative keyword order/name.
        lambda: model.apply_transaction(
            state=state,
            category=category,
            quantity=quantity,
            transaction_type="deposit",
        ),
    ]

    last_error = None

    for attempt in attempts:
        try:
            result = attempt()

            # Some model versions mutate the state and return None.
            if result is None:
                return state

            return result

        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            last_error = exc

    raise TypeError(
        "Could not call model.apply_transaction() with the expected "
        "deposit arguments. Last error: "
        f"{last_error}"
    )


def _metrics(state: Any) -> Dict[str, Any]:
    """Return the model metrics for a state."""
    result = model.compute_metrics(state)

    if not isinstance(result, dict):
        raise TypeError(
            "model.compute_metrics(state) must return a dictionary."
        )

    if "eco_score" not in result:
        raise KeyError(
            "model.compute_metrics(state) does not contain 'eco_score'."
        )

    return result


def _score(state: Any) -> float:
    """Return Eco-Balance score as a float."""
    value = _metrics(state)["eco_score"]

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


# ---------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------

def _maximum_quantity(
    category: str,
    definition: Dict[str, Any],
    max_trees: float,
    max_rain: float,
) -> float:
    """
    Calculate the maximum allowed quantity for a category.

    Explicit config limits are respected. The two UI controls are
    additionally enforced for trees and rainwater catchment.
    """

    configured_max = _get_number(
        definition,
        (
            "max_quantity",
            "max_qty",
            "maximum",
            "max",
            "capacity",
            "limit",
        ),
        None,
    )

    if configured_max is None:
        maximum = float("inf")
    else:
        maximum = max(0.0, configured_max)

    unit = _unit_size(definition)

    if _is_tree_category(category, definition):
        maximum = min(
            maximum,
            max(0.0, float(max_trees)) / unit,
        )

    if _is_rain_category(category, definition):
        maximum = min(
            maximum,
            max(0.0, float(max_rain)) / unit,
        )

    return maximum


# ---------------------------------------------------------------------
# Candidate evaluation
# ---------------------------------------------------------------------

def _candidate(
    state: Any,
    category: str,
    definition: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Test one transaction unit and calculate its marginal score gain.
    """

    unit = _unit_size(definition)
    cost = _unit_cost(category, definition)

    try:
        before_score = _score(state)
        after_state = _apply_deposit(
            _copy_state(state),
            category,
            unit,
        )
        after_score = _score(after_state)
    except Exception:
        return None

    gain = after_score - before_score

    return {
        "category": category,
        "label": _label(category, definition),
        "unit": unit,
        "unit_cost": cost,
        "score_gain": gain,
        "after_state": after_state,
        "score": after_score,
    }


def _best_candidate(
    state: Any,
    remaining: Dict[str, float],
    definitions: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Select the deposit with the best score improvement per rupee.

    Negative/zero score improvements are ignored.
    """

    candidates: List[Dict[str, Any]] = []

    for category, definition in definitions.items():
        if category not in remaining:
            continue

        if remaining[category] <= 0:
            continue

        candidate = _candidate(
            state,
            category,
            definition,
        )

        if candidate is None:
            continue

        gain = candidate["score_gain"]
        cost = candidate["unit_cost"]

        if gain <= 0:
            continue

        if cost <= 0:
            efficiency = float("inf")
        else:
            efficiency = gain / cost

        candidate["efficiency"] = efficiency
        candidates.append(candidate)

    if not candidates:
        return None

    candidates.sort(
        key=lambda x: (
            -x["efficiency"],
            -x["score_gain"],
            x["unit_cost"],
            x["category"],
        )
    )

    return candidates[0]


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------

def recommend(
    state: Any,
    target: float,
    max_trees: float,
    max_rain: float,
) -> Dict[str, Any]:
    """
    Build a deposit recommendation.

    Parameters
    ----------
    state:
        Current CampusState returned by ledger.replay().

    target:
        Desired Eco-Balance score.

    max_trees:
        Maximum number of trees allowed by the UI.

    max_rain:
        Maximum rainwater catchment area in m².

    Returns
    -------
    dict
        Structure expected by app.py:

        {
            "ok": bool,
            "plan": [
                {
                    "category": str,
                    "quantity": float,
                    "label": str,
                    "unit_cost": float,
                    "cost": float,
                }
            ],
            "total_cost": float,
            "before": {...},
            "after": {...},
        }
    """

    # -------------------------------------------------------------
    # Validate inputs
    # -------------------------------------------------------------

    target = float(target)
    max_trees = max(0.0, float(max_trees))
    max_rain = max(0.0, float(max_rain))

    target = max(0.0, min(100.0, target))

    definitions = _deposit_definitions()

    before_metrics = _metrics(state)
    before_score = float(before_metrics["eco_score"])

    # Already at target.
    if before_score >= target:
        return {
            "ok": True,
            "plan": [],
            "total_cost": 0.0,
            "before": before_metrics,
            "after": before_metrics,
        }

    if not definitions:
        return {
            "ok": False,
            "plan": [],
            "total_cost": 0.0,
            "before": before_metrics,
            "after": before_metrics,
        }

    # -------------------------------------------------------------
    # Calculate quantity limits
    # -------------------------------------------------------------

    remaining: Dict[str, float] = {}

    for category, definition in definitions.items():
        try:
            maximum = _maximum_quantity(
                category,
                definition,
                max_trees,
                max_rain,
            )

            if math.isfinite(maximum):
                remaining[category] = maximum
            else:
                # Safety limit for categories without an explicit
                # configured maximum.
                remaining[category] = 100000.0

        except Exception:
            continue

    if not remaining:
        return {
            "ok": False,
            "plan": [],
            "total_cost": 0.0,
            "before": before_metrics,
            "after": before_metrics,
        }

    # -------------------------------------------------------------
    # Greedy optimisation
    # -------------------------------------------------------------

    working_state = _copy_state(state)

    quantities: Dict[str, float] = {
        category: 0.0
        for category in remaining
    }

    total_cost = 0.0

    # Aggregate transactions by category.
    #
    # The algorithm evaluates one unit at a time initially. Once a
    # category is selected we try to take as many units as possible
    # while preserving the marginal-benefit calculation.
    #
    # A hard iteration cap prevents a malformed configuration from
    # creating an infinite loop.
    max_iterations = 10000

    for _ in range(max_iterations):
        current_score = _score(working_state)

        if current_score >= target:
            break

        candidate = _best_candidate(
            working_state,
            remaining,
            definitions,
        )

        if candidate is None:
            break

        category = candidate["category"]
        unit = candidate["unit"]
        cost = candidate["unit_cost"]

        if remaining[category] <= 0:
            break

        # Apply exactly one unit.
        working_state = candidate["after_state"]

        remaining[category] -= 1.0
        quantities[category] += unit
        total_cost += cost

    # -------------------------------------------------------------
    # Build plan
    # -------------------------------------------------------------

    plan: List[Dict[str, Any]] = []

    for category, quantity in quantities.items():
        if quantity <= 0:
            continue

        definition = definitions[category]
        unit_cost = _unit_cost(category, definition)

        plan.append(
            {
                "category": category,
                "label": _label(category, definition),
                "quantity": quantity,
                "unit_cost": unit_cost,
                "cost": quantity / _unit_size(definition) * unit_cost,
            }
        )

    # Put cheapest/high-impact categories first.
    plan.sort(
        key=lambda item: (
            -float(item["cost"] and item["quantity"] / item["cost"]),
            item["cost"],
            item["category"],
        )
    )

    after_metrics = _metrics(working_state)
    after_score = float(after_metrics["eco_score"])

    # -------------------------------------------------------------
    # Feasibility
    # -------------------------------------------------------------

    feasible = after_score >= target

    return {
        "ok": feasible,
        "plan": plan if feasible else plan,
        "total_cost": float(total_cost),
        "before": before_metrics,
        "after": after_metrics,
    }


# ---------------------------------------------------------------------
# Optional compatibility aliases
# ---------------------------------------------------------------------

def build_plan(
    state: Any,
    target: float,
    max_trees: float,
    max_rain: float,
) -> Dict[str, Any]:
    """Compatibility alias for older versions of the application."""
    return recommend(
        state,
        target,
        max_trees,
        max_rain,
    )


def get_recommendation(
    state: Any,
    target: float,
    max_trees: float,
    max_rain: float,
) -> Dict[str, Any]:
    """Compatibility alias for older versions of the application."""
    return recommend(
        state,
        target,
        max_trees,
        max_rain,
    )