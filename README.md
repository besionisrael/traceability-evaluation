# Distributed Traceability Evaluation

Realistic distributed simulation of the three traceability mechanisms.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  orchestrator                                                   │
│  - generates interactions                                       │
│  - routes to M_P / M_L / M_D                                   │
│  - collects IVR, EG, latency metrics                           │
└───────────┬───────────────────────────────┬────────────────────┘
            │ M_P / M_L                     │ M_D
            ▼                               ▼
┌──────────────────────┐        ┌──────────────────────────────┐
│  resource_r1  :5001  │◄───────│  coordinator         :6000   │
│  resource_r2  :5002  │◄───────│  - collects global state     │
│  resource_r3  :5003  │◄───────│  - n RTTs to resource nodes  │
└──────────────────────┘        │  - validates all constraints  │
                                │  - commits to target node     │
                                └──────────────────────────────┘
```

## Mechanism latency model

| Mechanism | Network cost | Validation cost |
|-----------|-------------|-----------------|
| M_P       | 1 RTT (target node only) | none |
| M_L       | 1 RTT (target node only) | local constraints O(1) |
| M_D       | n RTTs (all resource nodes) + 1 commit RTT | all constraints O(k·(n+m)) |

This produces the expected ordering: **M_P < M_L << M_D**,
which correctly reflects the architectural cost of global constraint enforcement.

## Running the evaluation

```bash
# Build and run all containers
docker compose up --build

# Results appear in ./results/ as JSON:
#   scenario1_results.json  — IVR vs concurrency
#   scenario2_results.json  — global constraint enforcement
#   scenario3_results.json  — latency scaling
```

## Quick run (fewer replications for testing)

```bash
N_REPLICATIONS=10 docker compose up --build
```

## Environment variables

| Variable        | Default       | Description                    |
|-----------------|--------------|--------------------------------|
| N_REPLICATIONS  | 100          | Number of random seeds per scenario |
| RESOURCE_ID     | r1           | Resource node identity         |
| PORT            | 5001/5002/... | TCP port for service           |

## Expected results (with Docker network latency)

- **M_P**: minimal latency (~0.1–0.5 ms), IVR > 0 under concurrency
- **M_L**: low latency (~0.1–0.5 ms + local eval), IVR > 0 for global constraints
- **M_D**: high latency (~3–10 ms due to n round-trips), IVR = 0 always

The key difference from the original simulation: M_D is now meaningfully
slower than M_L because it must contact all resource nodes before admitting
any interaction. This reflects the real architectural cost.
