# Oxygen Bank — Sustainable Development Prototype

This version changes the core live model from a simple sustainability score into a **Sustainable Development Decision Engine**:

`Existing campus → Proposed development → BAU impact → Eco-Balance → Weakness → Intervention → Sustainable scenario`

## Main inputs

- Total site area
- Existing built-up area
- Proposed new construction
- Current population/users
- Additional population/users
- Existing trees
- Existing green-cover area
- Green area removed by construction
- Current annual water consumption
- Additional annual water demand
- Annual rainwater harvested
- Annual recycled/reused water
- Annual electricity consumption
- Annual renewable electricity
- Additional electricity from the new development

## Main outputs

- Current Eco-Balance
- BAU Eco-Balance after development
- Carbon, Water and Cooling/Green Cover pillar scores
- Development impacts and gaps
- Primary pressure/weakest pillar
- Recommended interventions
- Interactive BAU → sustainable scenario simulator
- Before/after improvement

## Decision bands

- 75–100: Balanced Development
- 60–75: Transition
- 40–60: High Environmental Pressure
- 0–40: Ecological Stress

These bands and prototype benchmarks are configurable and are **not universal regulatory standards**.

## Run

```bash
python3 -m pip install -r requirements.txt
streamlit run app.py
```
