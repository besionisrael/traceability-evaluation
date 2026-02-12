# Traceability Evaluation - File Manifest

Generated artifacts for numerical evaluation of directed traceability mechanisms.

## Core Components (core/)

| File | Description | Lines |
|------|-------------|-------|
| `state.py` | SystemState, PermissionRecord, LocalView classes | ~100 |
| `interaction.py` | Interaction class (Definition 3.4) | ~20 |
| `constraints.py` | C_excl, C_auth, C_global implementations | ~150 |
| `__init__.py` | Module exports | ~20 |

## Mechanisms (mechanisms/)

| File | Description | Lines |
|------|-------------|-------|
| `descriptive.py` | M_P - Descriptive mechanism (Definition 3.7) | ~90 |
| `local.py` | M_L - Locally-validated mechanism (Definition 3.9) | ~100 |
| `directed.py` | M_D - Directed mechanism (Definition 3.10) | ~120 |
| `__init__.py` | Module exports | ~10 |

## Evaluation Scenarios (scenarios/)

| File | Description | Lines |
|------|-------------|-------|
| `scenario1.py` | IVR vs Concurrency (Theorems 5.1, 5.2) | ~180 |
| `scenario2.py` | Global Constraints (Theorem 5.3) | ~220 |
| `scenario3.py` | Latency Scaling (Theorems 5.4, 5.5) | ~250 |
| `__init__.py` | Module exports | ~10 |

## Scripts

| File | Description | Lines |
|------|-------------|-------|
| `run_evaluation.py` | Main script - runs all scenarios | ~200 |
| `test_basic.py` | Unit tests for core components | ~150 |
| `quick_test.py` | Quick validation (1 replication each) | ~50 |

## Documentation

| File | Description |
|------|-------------|
| `README.md` | Usage instructions and overview |
| `EXPECTED_RESULTS.md` | Expected results from paper (Tables 1-3) |
| `requirements.txt` | Python dependencies |
| `.gitignore` | Git ignore rules |

## Total

- **17 Python files** (~1,700 lines of code)
- **4 documentation files**
- All theorems (5.1-5.5) have corresponding test implementations
- 100% reproducibility with fixed random seeds

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run unit tests
python test_basic.py

# Quick validation (1 replication)
python quick_test.py

# Full evaluation (100 replications, ~5-10 min)
python run_evaluation.py
```

## Validation Status

✓ All unit tests passing
✓ Quick test validates all scenarios work
✓ Code implements formal definitions from Sections 3-4
✓ Evaluation implements scenarios from Section 6
