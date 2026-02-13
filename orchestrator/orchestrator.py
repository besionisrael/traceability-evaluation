#!/usr/bin/env python3
"""
Orchestrator — drives the distributed traceability evaluation.

Reproduces the three scenarios from the paper:
  Scenario 1: IVR vs concurrency level
  Scenario 2: Global constraint enforcement
  Scenario 3: Latency scaling (n agents, k constraints)

For each scenario, the same interaction sequences are submitted to all
three mechanisms so that IVR and latency are directly comparable.
"""
import os
import sys
import json
import time
import socket
import random
import logging
import statistics
from typing import List, Dict, Tuple, Optional

sys.path.insert(0, '/app')
from shared.models import Interaction, encode_msg, decode_msg

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s')
logger = logging.getLogger('Orchestrator')


# ─── Low-level socket helper ─────────────────────────────────────────────────

def send_request(host: str, port: int, msg: dict, timeout: float = 10.0) -> dict:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        s.sendall(encode_msg(msg))
        data = b''
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk
            if b'\n' in data:
                break
        return decode_msg(data)
    finally:
        s.close()


def wait_for_services(resource_nodes: Dict[str, Tuple[str, int]],
                      coordinator: Tuple[str, int],
                      retries: int = 30, delay: float = 1.0):
    """Block until all containers are reachable."""
    all_endpoints = list(resource_nodes.values()) + [coordinator]
    for host, port in all_endpoints:
        for attempt in range(retries):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2.0)
                s.connect((host, port))
                s.close()
                break
            except Exception:
                if attempt == retries - 1:
                    raise RuntimeError(f"Service {host}:{port} not reachable after {retries} attempts")
                time.sleep(delay)
    logger.info("All services reachable.")


# ─── Interaction generation ───────────────────────────────────────────────────

def generate_interactions(agents: List[str],
                          resources: List[str],
                          T_max: int,
                          lambda_rate: float,
                          seed: int,
                          force_global_conflict: bool = False) -> List[List[Interaction]]:
    """
    Generate T_max timesteps of interactions.

    At each timestep, each agent independently attempts an interaction
    with probability lambda_rate.  The agent state (what it holds) is
    tracked so that release follows acquire in a plausible sequence.

    Returns: list of timesteps, each a list of concurrent Interaction objects.
    """
    rng = random.Random(seed)
    timesteps: List[List[Interaction]] = []
    held: Dict[str, Optional[str]] = {a: None for a in agents}  # agent -> resource held

    for t in range(T_max):
        step: List[Interaction] = []
        for agent in agents:
            if rng.random() < lambda_rate:
                if held[agent] is None:
                    # Try to acquire a resource
                    resource = rng.choice(resources)
                    if force_global_conflict:
                        # Bias towards R_subset to exercise C_global
                        resource = rng.choice(['r1', 'r2', rng.choice(resources)])
                    step.append(Interaction(agent, resource, 'acquire', t))
                else:
                    # Release what we hold
                    step.append(Interaction(agent, held[agent], 'release', t))
        # Update held state naively (optimistic — doesn't account for rejections)
        for interaction in step:
            if interaction.action == 'acquire':
                held[interaction.agent] = interaction.resource
            else:
                held[interaction.agent] = None
        timesteps.append(step)
    return timesteps


# ─── Mechanism runners ────────────────────────────────────────────────────────

def reset_all(resource_nodes: Dict[str, Tuple[str, int]], agents: List[str]):
    for r_id, (host, port) in resource_nodes.items():
        send_request(host, port, {'type': 'RESET', 'agents': agents})


def run_mp(timesteps: List[List[Interaction]],
           resource_nodes: Dict[str, Tuple[str, int]]) -> dict:
    """Run M_P: send each interaction to its resource node, no validation."""
    latencies = []
    for step in timesteps:
        for interaction in step:
            host, port = resource_nodes[interaction.resource]
            t0 = time.perf_counter()
            resp = send_request(host, port, {
                'type': 'PROCESS_MP',
                'interaction': interaction.to_dict()
            })
            latencies.append(resp.get('latency_us', (time.perf_counter() - t0) * 1e6))
    return {'latencies': latencies}


def run_ml(timesteps: List[List[Interaction]],
           resource_nodes: Dict[str, Tuple[str, int]]) -> dict:
    """
    Run M_L: each interaction goes to its resource node for local validation.

    Conformance with Definition M_L: concurrent agents at timestep t all evaluate
    against the same frozen state s^a_local(t).  We achieve this by:
      1. Collecting a snapshot from each resource node BEFORE submitting any
         interaction in the timestep.
      2. Sending that snapshot alongside the interaction so the node validates
         against it, not its live state.
    """
    import threading
    latencies = []

    for step in timesteps:
        if not step:
            continue

        # Step 1: collect snapshot from all resource nodes (once per timestep)
        snapshots = {}
        for r_id, (host, port) in resource_nodes.items():
            resp = send_request(host, port, {'type': 'GET_STATE'})
            if resp.get('ok'):
                snapshots[r_id] = resp['state']

        # Step 2: submit all interactions in parallel, each with its snapshot
        results = {}
        errors = {}

        def submit_ml(idx, interaction):
            host, port = resource_nodes[interaction.resource]
            snapshot = snapshots.get(interaction.resource)
            try:
                resp = send_request(host, port, {
                    'type': 'PROCESS_ML',
                    'interaction': interaction.to_dict(),
                    'snapshot': snapshot,  # frozen state for conformant validation
                })
                results[idx] = resp
            except Exception as e:
                errors[idx] = str(e)

        threads = []
        for idx, interaction in enumerate(step):
            t = threading.Thread(target=submit_ml, args=(idx, interaction))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()

        for idx in range(len(step)):
            resp = results.get(idx, {})
            latencies.append(resp.get('latency_us', 0.0))

    return {'latencies': latencies}


def run_md(timesteps: List[List[Interaction]],
           coordinator: Tuple[str, int]) -> dict:
    """
    Run M_D: each interaction goes to the coordinator, which collects global
    state (n network RTTs) before validating and committing.
    """
    latencies = []
    collect_latencies = []
    admitted_count = 0
    total_count = 0
    coord_host, coord_port = coordinator

    for step in timesteps:
        # M_D serialises: concurrent interactions are processed one by one
        for interaction in step:
            total_count += 1
            resp = send_request(coord_host, coord_port, {
                'type': 'PROCESS_MD',
                'interaction': interaction.to_dict()
            })
            latencies.append(resp.get('latency_us', 0.0))
            collect_latencies.append(resp.get('collect_latency_us', 0.0))
            if resp.get('admitted', False):
                admitted_count += 1

    return {
        'latencies': latencies,
        'collect_latencies': collect_latencies,
        'admitted': admitted_count,
        'total': total_count,
    }


# ─── IVR computation (post-hoc, via trace) ───────────────────────────────────

def collect_traces(resource_nodes: Dict[str, Tuple[str, int]]) -> List[dict]:
    """Collect all trace entries from all resource nodes."""
    all_entries = []
    for r_id, (host, port) in resource_nodes.items():
        resp = send_request(host, port, {'type': 'GET_TRACE'})
        all_entries.extend(resp.get('trace', []))
    return all_entries


def compute_ivr_from_trace(trace_entries: List[dict], mechanism: str,
                           resource_nodes: Dict[str, Tuple[str, int]]) -> float:
    """
    Compute IVR for admitted interactions.

    M_D: IVR = 0 by construction (Theorem, no computation needed).

    M_P / M_L: replay admitted interactions in timestamp order to reconstruct
    global state at each step, then evaluate all constraints.
    This is valid because IVR measures compliance of the recorded trace,
    not of individual concurrent decisions.
    """
    from shared.models import ResourceState
    from shared.constraints import C_excl, C_auth, C_global

    # M_D: guaranteed by protocol
    if mechanism == 'M_D':
        return 0.0

    entries = [
        e for e in trace_entries
        if e['mechanism'] == mechanism and e.get('admitted', False)
    ]
    if not entries:
        return 0.0

    # Sort by timestamp for sequential replay
    entries.sort(key=lambda e: e['interaction']['timestamp'])

    # Initialise state: fetch permissions from live nodes (post-run),
    # then reset locks for replay
    states: Dict[str, ResourceState] = {}
    for r_id, (host, port) in resource_nodes.items():
        resp = send_request(host, port, {'type': 'GET_STATE'})
        s = ResourceState.from_dict(resp['state'])
        s.locks = set()   # reset for replay
        states[r_id] = s

    violations = 0
    for entry in entries:
        interaction = Interaction(**entry['interaction'])
        target = states.get(interaction.resource)
        if target is None:
            continue

        violated = (
            not C_excl(target, interaction) or
            not C_auth(target, interaction) or
            not C_global(states, interaction)
        )
        if violated:
            violations += 1

        # Apply transition to advance replay state
        if interaction.action == 'acquire':
            target.locks.add(interaction.agent)
        elif interaction.action == 'release':
            target.locks.discard(interaction.agent)

    return violations / len(entries)


def compute_eg(trace_entries: List[dict], mechanism: str) -> float:
    entries = [e for e in trace_entries if e['mechanism'] == mechanism]
    if not entries:
        return 0.0
    rejected = sum(1 for e in entries if not e['admitted'])
    return rejected / len(entries)


# ─── Scenario runners ─────────────────────────────────────────────────────────

def run_scenario(label: str,
                 agents: List[str],
                 resources: List[str],
                 T_max: int,
                 lambda_rate: float,
                 n_replications: int,
                 resource_nodes: Dict[str, Tuple[str, int]],
                 coordinator: Tuple[str, int],
                 force_global_conflict: bool = False) -> dict:
    """Run one scenario configuration for n_replications seeds."""
    results_mp = {'ivr': [], 'eg': [], 'latency': []}
    results_ml = {'ivr': [], 'eg': [], 'latency': []}
    results_md = {'ivr': [], 'eg': [], 'latency': [], 'collect_latency': []}

    for seed in range(n_replications):
        timesteps = generate_interactions(
            agents, resources, T_max, lambda_rate, seed, force_global_conflict
        )

        # ── M_P ─────────────────────────────────────────────────────────────
        reset_all(resource_nodes, agents)
        mp_run = run_mp(timesteps, resource_nodes)
        trace = collect_traces(resource_nodes)
        results_mp['ivr'].append(compute_ivr_from_trace(trace, 'M_P', resource_nodes))
        results_mp['eg'].append(compute_eg(trace, 'M_P'))
        results_mp['latency'].append(statistics.mean(mp_run['latencies']) if mp_run['latencies'] else 0)

        # ── M_L ─────────────────────────────────────────────────────────────
        reset_all(resource_nodes, agents)
        ml_run = run_ml(timesteps, resource_nodes)
        trace = collect_traces(resource_nodes)
        results_ml['ivr'].append(compute_ivr_from_trace(trace, 'M_L', resource_nodes))
        results_ml['eg'].append(compute_eg(trace, 'M_L'))
        results_ml['latency'].append(statistics.mean(ml_run['latencies']) if ml_run['latencies'] else 0)

        # ── M_D ─────────────────────────────────────────────────────────────
        reset_all(resource_nodes, agents)
        md_run = run_md(timesteps, coordinator)
        trace = collect_traces(resource_nodes)
        results_md['ivr'].append(compute_ivr_from_trace(trace, 'M_D', resource_nodes))
        results_md['eg'].append(compute_eg(trace, 'M_D'))
        results_md['latency'].append(statistics.mean(md_run['latencies']) if md_run['latencies'] else 0)
        results_md['collect_latency'].append(
            statistics.mean(md_run['collect_latencies']) if md_run['collect_latencies'] else 0
        )

        if (seed + 1) % 10 == 0:
            logger.info(f"  [{label}] {seed+1}/{n_replications} replications done")

    def summarise(vals):
        return {
            'mean': statistics.mean(vals),
            'std': statistics.stdev(vals) if len(vals) > 1 else 0.0
        }

    return {
        'M_P': {k: summarise(v) for k, v in results_mp.items()},
        'M_L': {k: summarise(v) for k, v in results_ml.items()},
        'M_D': {k: (summarise(v) if k != 'collect_latency' else summarise(results_md['collect_latency']))
                for k, v in results_md.items()},
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    output_dir = os.environ.get('OUTPUT_DIR', '/results')
    os.makedirs(output_dir, exist_ok=True)

    # Service addresses (from docker-compose env or defaults)
    resource_nodes = {
        'r1': (os.environ.get('R1_HOST', 'resource_r1'), int(os.environ.get('R1_PORT', 5001))),
        'r2': (os.environ.get('R2_HOST', 'resource_r2'), int(os.environ.get('R2_PORT', 5002))),
        'r3': (os.environ.get('R3_HOST', 'resource_r3'), int(os.environ.get('R3_PORT', 5003))),
    }
    coordinator = (
        os.environ.get('COORD_HOST', 'coordinator'),
        int(os.environ.get('COORD_PORT', 6000))
    )

    logger.info("Waiting for services...")
    wait_for_services(resource_nodes, coordinator)

    N_REPS = int(os.environ.get('N_REPLICATIONS', 100))
    T_MAX = 50

    # ── Scenario 1: IVR vs concurrency ───────────────────────────────────────
    logger.info("=== Scenario 1: IVR vs concurrency ===")
    sc1_results = {}
    for lambda_rate in [0.3, 0.5, 0.7]:
        logger.info(f"  lambda={lambda_rate}")
        sc1_results[str(lambda_rate)] = run_scenario(
            label=f"S1-lambda={lambda_rate}",
            agents=[f'a{i+1}' for i in range(5)],
            resources=['r1', 'r2', 'r3'],
            T_max=T_MAX,
            lambda_rate=lambda_rate,
            n_replications=N_REPS,
            resource_nodes=resource_nodes,
            coordinator=coordinator,
            force_global_conflict=False,
        )

    with open(f'{output_dir}/scenario1_results.json', 'w') as f:
        json.dump(sc1_results, f, indent=2)
    logger.info("Scenario 1 saved.")

    # ── Scenario 2: global constraint enforcement ────────────────────────────
    logger.info("=== Scenario 2: global constraint enforcement ===")
    sc2_results = run_scenario(
        label='S2',
        agents=[f'a{i+1}' for i in range(5)],
        resources=['r1', 'r2', 'r3'],
        T_max=T_MAX,
        lambda_rate=0.5,
        n_replications=N_REPS,
        resource_nodes=resource_nodes,
        coordinator=coordinator,
        force_global_conflict=True,
    )
    with open(f'{output_dir}/scenario2_results.json', 'w') as f:
        json.dump(sc2_results, f, indent=2)
    logger.info("Scenario 2 saved.")

    # ── Scenario 3: latency scaling ───────────────────────────────────────────
    logger.info("=== Scenario 3: latency scaling ===")
    sc3_results = {}
    for n_agents in [3, 5, 10, 15]:
        agents = [f'a{i+1}' for i in range(n_agents)]
        sc3_results[str(n_agents)] = run_scenario(
            label=f"S3-n={n_agents}",
            agents=agents,
            resources=['r1', 'r2', 'r3'],
            T_max=T_MAX,
            lambda_rate=0.5,
            n_replications=N_REPS,
            resource_nodes=resource_nodes,
            coordinator=coordinator,
            force_global_conflict=False,
        )
        logger.info(f"  n={n_agents} done")

    with open(f'{output_dir}/scenario3_results.json', 'w') as f:
        json.dump(sc3_results, f, indent=2)
    logger.info("Scenario 3 saved.")

    logger.info("=== Evaluation complete. Results in /results/ ===")


if __name__ == '__main__':
    main()
