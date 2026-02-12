# Directed Traceability Evaluation

Numerical evaluation code for the paper "Directed Traceability in Distributed Systems: A Formal Framework for Designing Constraint-Enforcing Interactions"

## Structure

```
traceability_evaluation/
├── core/                   # Core components
│   ├── state.py           # SystemState, PermissionRecord, LocalView
│   ├── interaction.py     # Interaction class
│   └── constraints.py     # C_excl, C_auth, C_global
├── mechanisms/            # Mechanism implementations
│   ├── descriptive.py     # M_P (descriptive traceability)
│   ├── local.py           # M_L (locally-validated)
│   └── directed.py        # M_D (directed traceability)
├── scenarios/             # Evaluation scenarios
│   ├── scenario1.py       # IVR vs concurrency (Theorems 5.1, 5.2)
│   ├── scenario2.py       # Global constraints (Theorem 5.3)
│   └── scenario3.py       # Latency scaling (Theorems 5.4, 5.5)
├── run_evaluation.py      # Main script
└── requirements.txt
```

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Run all scenarios

```bash
python run_evaluation.py [output_dir]
```

This will:
- Run all three scenarios (100 replications each)
- Print results to console
- Save detailed results as JSON to `output_dir/` (default: `results/`)

Estimated runtime: ~5-10 minutes (depending on CPU)

### Run individual scenarios

```bash
# Scenario 1: IVR vs concurrency
python -m scenarios.scenario1

# Scenario 2: Global constraints
python -m scenarios.scenario2

# Scenario 3: Latency scaling
python -m scenarios.scenario3
```

## Scenarios

### Scenario 1: Violation Rate vs Concurrency

**Objective**: Validate Theorems 5.1 and 5.2

**Configuration**:
- n = 5 agents
- m = 3 resources
- λ ∈ {0.3, 0.5, 0.7} (concurrency levels)
- Constraints: C_excl, C_auth
- 100 replications per λ

**Expected results**:
- M_D: IVR = 0.000 for all λ (Theorem 5.1)
- M_P: IVR ∈ [0.17, 0.37], increasing with λ (Theorem 5.2)
- M_L: IVR ∈ [0.02, 0.09], intermediate

### Scenario 2: Global Constraint Enforcement

**Objective**: Validate Theorem 5.3

**Configuration**:
- n = 5 agents
- m = 3 resources
- λ = 0.5
- Constraints: C_excl, C_auth, **C_global** (max 2 agents on {r1, r2})
- 100 replications

**Expected results**:
- M_D: IVR = 0.000, no violations
- M_L: IVR ≈ 0.24, with ~86% violations from C_global (Theorem 5.3)
- M_P: IVR ≈ 0.32, violations from all constraint types

### Scenario 3: Latency Scaling

**Objective**: Validate Theorems 5.4 and 5.5

**Configuration**:
- n ∈ {3, 5, 10, 15} agents
- m = 3 resources
- k ∈ {2, 3, 5} constraints
- λ = 0.5
- 100 replications per (n, k) pair

**Expected results**:
- Linear scaling: L ∝ n (R² ≈ 0.98), L ∝ k (R² ≈ 0.99) (Theorem 5.4)
- Trade-off (n=5, k=3): M_D ~27× slower than M_P, but IVR: 28% → 0% (Theorem 5.5)

## Output Format

Results are saved as JSON files:

```json
{
  "M_P": {
    "IVR": {"mean": 0.284, "std": 0.031},
    "EG": {"mean": 0.0, "std": 0.0},
    "trace_length": {"mean": 142, "std": 15}
  },
  "M_L": { ... },
  "M_D": { ... }
}
```

## Implementation Notes

### Atomicity (Section 4.1.2)

M_D processes concurrent interactions serially (total serialization):
```python
sorted_interactions = sorted(timestep_interactions, key=lambda u: u.agent)
for interaction in sorted_interactions:
    state = m_d.process_interaction(state, interaction)
```

### Constraints (Section 4.2)

- **C_excl**: Local - resource can be held by at most one agent
- **C_auth**: Local - agent must have valid permission
- **C_global**: Global - max K_max=2 agents on R_subset={r1, r2}

### Latency Measurement (Section 5.3)

Latency measured in microseconds using `time.perf_counter()`:
```python
start = time.perf_counter()
result = evaluate_all_constraints(state, interaction)
end = time.perf_counter()
latency_us = (end - start) * 1e6
```

## Reproducibility

All scenarios use fixed random seeds (0-99 for 100 replications) to ensure reproducibility. Same interaction sequences are used for all three mechanisms in each replication.

## Citation

If you use this code, please cite:

```bibtex
@article{sion2024directed,
  title={Directed Traceability in Distributed Systems: A Formal Framework for Designing Constraint-Enforcing Interactions},
  author={Sion, Sion Israel and April, Alain and Zhang, Kaiwen},
  journal={IEEE Access},
  year={2024}
}
```
