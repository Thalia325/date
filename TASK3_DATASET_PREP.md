# Task 3: reaction-condition tables and experiment-parameter KIE

## Objective

Clean and screen datasets for chemistry and chemical-engineering records that can support extraction of:

- reactants, products, catalysts, reagents, and solvents
- temperature, time, pH, pressure, yield, selectivity, conversion, and molar ratio
- experiment/entry/run identifiers
- operation steps and balanced equations when available
- table-cell, text-span, or structured-record evidence

## Dataset roles

| Dataset | Decision | Main use |
|---|---|---|
| ChemTable | Core keep | Visual chemical table understanding; prioritize condition-optimization, substrate-screening, and reaction-feature tables. |
| ChemTables | Keep as router | Patent table type classification and negative sampling before field-level KIE. |
| ChEMU | Core keep | Patent text entity and reaction-step KIE; maps well to materials, reagent/catalyst, product, solvent, temperature, time, and yield fields. |
| ORD / ORDerly | Keep as schema reference | Structured reaction schema, normalization target, and benchmark for conditions/yields. |
| Solid-state synthesis recipes | Keep as experiment-parameter reference | Materials synthesis operations, conditions, starting compounds, target material, and balanced equation JSON examples. |

## Directory convention

Place raw data under these directories:

```text
data/raw/ChemTable
data/raw/ChemTables
data/raw/ChEMU
data/raw/ORD
data/raw/ORDerly
data/raw/SolidStateSynthesisRecipes
```

The audit script also accepts `data/raw/solid-state-synthesis-recipes` for the recipes dataset.

## Cleaning rule

Keep records that contain reaction-condition or experiment-parameter signals:

- reaction, condition optimization, substrate screening, reaction feature, synthesis, catalyst, reagent, solvent, product, reactant
- temperature, time, pH, pressure, yield, selectivity, conversion, molar ratio, equivalent, operation
- ChEMU entity types such as `STARTING_MATERIAL`, `REAGENT_CATALYST`, `REACTION_PRODUCT`, `SOLVENT`, `TEMPERATURE`, `TIME`, `YIELD_PERCENT`, and `YIELD_OTHER`
- recipe JSON fields such as `target_material`, `starting_compounds`, `operations`, `conditions`, and `balanced_equation`

Drop or de-prioritize bibliography, funding, table-of-contents, pure statistics, and records with no chemical role or experimental parameter evidence.

## Commands

```powershell
python scripts\audit_task3_datasets.py
```

Outputs:

```text
data/reports/task3_local_audit.md
data/processed/task3_dataset_manifest.csv
data/processed/task3_kie_schema.json
```

## Next converters

After raw data is mounted locally, add dataset-specific converters:

- `convert_chemtable_to_task3_kie.py`: table/cell/QA annotation to row-level reaction-condition JSON.
- `convert_chemtables_to_task3_router.py`: table semantic label to keep/drop/routing labels.
- `convert_chemu_to_task3_kie.py`: patent snippets and entity spans to reaction-step JSON.
- `convert_ord_to_task3_reference.py`: ORD/ORDerly records to the normalized target schema.
- `convert_solid_state_recipes_to_task3_kie.py`: recipe JSON to synthesis operation/condition JSON.
