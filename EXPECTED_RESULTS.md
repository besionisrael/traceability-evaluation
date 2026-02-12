# Expected Results from Paper

This file documents the expected results reported in Section 6 of the paper.

## Scenario 1: IVR vs Concurrency Level (Table 1, Figure 1)

**Configuration**: n=5, m=3, k=2 (C_excl, C_auth), T_max=50, 100 replications

### Table: Violation Rate (IVR) as Function of Concurrency

| Mechanism | λ=0.3 (low) | λ=0.5 (medium) | λ=0.7 (high) |
|-----------|-------------|----------------|--------------|
| M_D       | 0.000±0.000 | 0.000±0.000    | 0.000±0.000  |
| M_L       | 0.023±0.008 | 0.041±0.012    | 0.089±0.018  |
| M_P       | 0.169±0.024 | 0.284±0.031    | 0.366±0.041  |

**Key findings**:
- M_D maintains IVR = 0 across all concurrency levels (Theorem 5.1 ✓)
- M_P exhibits IVR ∈ [16.9%, 36.6%] increasing with λ (Theorem 5.2 ✓)
- M_L shows intermediate behavior with IVR ∈ [2.3%, 8.9%]

### Table: Enforcement Gap (EG) and Trace Length (λ=0.7)

| Mechanism | EG          | |τ| (avg)   |
|-----------|-------------|-------------|
| M_D       | 0.341±0.028 | 115±12      |
| M_L       | 0.187±0.021 | 142±15      |
| M_P       | 0.000±0.000 | 175±18      |

---

## Scenario 2: Global Constraint Enforcement (Table 2, Figure 2)

**Configuration**: n=5, m=3, λ=0.5, k=3 (C_excl, C_auth, **C_global**), 100 replications
**C_global**: Max 2 agents on R_subset = {r1, r2}

### Table: Performance with Multi-Resource Constraint

| Mechanism | IVR (%) | C_global violations | C_excl violations | |τ|     |
|-----------|---------|---------------------|-------------------|---------|
| M_D       | 0.0     | 0                   | 0                 | 88±9    |
| M_L       | **24.3**| **21**              | 3                 | 123±13  |
| M_P       | 31.7    | 26                  | 13                | 137±14  |

**Key findings**:
- M_L: 86% of violations are from C_global (21/24.3) (Theorem 5.3 ✓)
- Despite successful local validation, M_L produces IVR = 24.3%
- M_D maintains IVR = 0 even with global constraints

---

## Scenario 3: Latency Scaling (Table 3, Figures 3-4)

**Configuration**: n ∈ {3,5,10,15}, k ∈ {2,3,5}, m=3, λ=0.5, 100 replications

### Table: Average Latency (μs) as Function of n and k

| n (agents) | k=2 (M_D) | k=3 (M_D) | k=5 (M_D) | M_L      | M_P      |
|------------|-----------|-----------|-----------|----------|----------|
| 3          | 12.3±1.2  | 18.7±1.8  | 31.2±2.4  | 4.8±0.6  | 0.9±0.1  |
| 5          | 15.8±1.5  | 24.1±2.1  | 40.6±3.2  | 5.1±0.7  | 0.9±0.1  |
| 10         | 23.4±2.1  | 35.8±3.0  | 59.9±4.8  | 5.6±0.8  | 1.0±0.1  |
| 15         | 31.2±2.8  | 47.6±4.1  | 79.4±6.3  | 6.2±0.9  | 1.0±0.1  |

### Linear Regression (k=3)

**Latency vs n**: L = 3.2n + 9.1 (R² = 0.98) ✓ confirms O(n)
**Latency vs k** (n=5): L = 7.8k + 0.4 (R² = 0.99) ✓ confirms O(k)

Both regressions validate Theorem 5.4: L_val(M_D) = O(k·(n+m))

### Trade-off Synthesis (n=5, k=3)

| Mechanism | Latency (μs) | IVR (%)  | Trade-off              |
|-----------|--------------|----------|------------------------|
| M_P       | 0.9          | 28.4     | Fast but violations    |
| M_L       | 5.1          | 4.1      | Intermediate           |
| M_D       | 24.1         | **0.0**  | **Guaranteed compliance** |

**Slowdown factors**:
- M_D vs M_P: 24.1/0.9 ≈ **27×**
- M_D vs M_L: 24.1/5.1 ≈ **5×**

**Trade-off** (Theorem 5.5 ✓): M_D pays 27× latency factor but eliminates 100% of violations (28.4% → 0%)

---

## Summary of Theorem Validation

| Theorem | Statement | Status |
|---------|-----------|--------|
| 5.1 | IVR(M_D) = 0 | ✓ Validated (all scenarios, 300 runs, IVR = 0.000) |
| 5.2 | IVR(M_P) > 0 under concurrency | ✓ Validated (IVR ∈ [16.9%, 36.6%]) |
| 5.3 | IVR(M_L) > 0 with global constraints | ✓ Validated (IVR = 24.3%, 86% from C_global) |
| 5.4 | L(M_D) = O(k·(n+m)) | ✓ Validated (R² > 0.98 for both n and k) |
| 5.5 | Latency-compliance trade-off | ✓ Validated (27× factor, 28.4% → 0%) |

---

## Notes on Running Full Evaluation

Expected runtime: ~5-10 minutes for all scenarios (100 replications each)

To reproduce these results:
```bash
python run_evaluation.py results/
```

Results will be saved to `results/scenario{1,2,3}_results.json`

Variability: Due to stochastic interaction generation, exact values may vary slightly but should be within reported ±std ranges.
