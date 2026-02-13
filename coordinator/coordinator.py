#!/usr/bin/env python3
"""
M_D Coordinator — global validation coordinator.

For each interaction:
  1. Query ALL resource nodes to collect global state  (n network RTTs)
  2. Evaluate all constraints on aggregated state
  3. COMMIT result to the target resource node
  4. Return admit/reject + measured latency

This is where M_D's real latency cost materialises: n round-trips over the
network before any admission decision can be made.
"""
import os
import sys
import json
import socket
import threading
import time
import logging
from typing import Dict, List

sys.path.insert(0, '/app')
from shared.models import ResourceState, Interaction, encode_msg, decode_msg
from shared.constraints import evaluate_global

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s')


def send_request(host: str, port: int, msg: dict, timeout: float = 5.0) -> dict:
    """Send one JSON request over TCP and return the response."""
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


class Coordinator:
    """
    M_D global coordinator.

    resource_nodes: dict mapping resource_id -> (host, port)
    """

    def __init__(self, resource_nodes: Dict[str, tuple]):
        self.resource_nodes = resource_nodes  # {r_id: (host, port)}
        self.logger = logging.getLogger('Coordinator')
        self.lock = threading.Lock()

    # ── Global state collection ───────────────────────────────────────────────

    def collect_global_state(self) -> Dict[str, ResourceState]:
        """
        Query every resource node for its current state.
        This is the dominant cost of M_D: one RTT per resource node.
        """
        results = {}
        errors = {}

        def fetch(r_id, host, port):
            try:
                resp = send_request(host, port, {'type': 'GET_STATE'})
                if resp.get('ok'):
                    results[r_id] = ResourceState.from_dict(resp['state'])
                else:
                    errors[r_id] = resp.get('error', 'unknown')
            except Exception as e:
                errors[r_id] = str(e)

        # Fire all queries in parallel (still pays RTT latency for the slowest)
        threads = []
        for r_id, (host, port) in self.resource_nodes.items():
            t = threading.Thread(target=fetch, args=(r_id, host, port))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()

        if errors:
            self.logger.warning(f"State collection errors: {errors}")

        return results

    # ── M_D validation ────────────────────────────────────────────────────────

    def process_interaction(self, interaction: Interaction) -> dict:
        """
        Full M_D protocol:
          1. Collect global state (network I/O)
          2. Evaluate all constraints
          3. COMMIT to target resource node
        Returns: {admitted, latency_us, collect_latency_us, eval_latency_us}
        """
        t_start = time.perf_counter()

        # Step 1: collect global state (n RTTs — the real cost)
        t0 = time.perf_counter()
        all_states = self.collect_global_state()
        collect_us = (time.perf_counter() - t0) * 1e6

        # Step 2: evaluate constraints on aggregated state
        t1 = time.perf_counter()
        with self.lock:   # serialise decisions to avoid TOCTOU races
            admitted = evaluate_global(all_states, interaction)
            eval_us = (time.perf_counter() - t1) * 1e6

            # Serialize snapshot for trace storage (only target resource state)
            target_snapshot = all_states.get(interaction.resource)
            target_snapshot_dict = target_snapshot.to_dict() if target_snapshot else None

            # Step 3: commit to target resource node
            target_host, target_port = self.resource_nodes[interaction.resource]
            send_request(target_host, target_port, {
                'type': 'COMMIT',
                'interaction': interaction.to_dict(),
                'admitted': admitted,
                'state_snapshot': target_snapshot_dict,
            })

        total_us = (time.perf_counter() - t_start) * 1e6
        return {
            'admitted': admitted,
            'latency_us': total_us,
            'collect_latency_us': collect_us,
            'eval_latency_us': eval_us,
        }

    # ── TCP server ────────────────────────────────────────────────────────────

    def dispatch(self, msg: dict) -> dict:
        req_type = msg.get('type')
        if req_type == 'PROCESS_MD':
            return self.process_interaction(Interaction.from_dict(msg['interaction']))
        elif req_type == 'PING':
            return {'ok': True}
        else:
            return {'ok': False, 'error': f'Unknown type: {req_type}'}

    def serve(self, host: str = '0.0.0.0', port: int = 6000):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen(100)
        self.logger.info(f"Coordinator listening on {host}:{port}")

        while True:
            conn, addr = server.accept()
            threading.Thread(
                target=self._handle_connection,
                args=(conn,),
                daemon=True
            ).start()

    def _handle_connection(self, conn: socket.socket):
        try:
            data = b''
            while True:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b'\n' in data:
                    break
            if data:
                msg = decode_msg(data)
                response = self.dispatch(msg)
                conn.sendall(encode_msg(response))
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
        finally:
            conn.close()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 6000))

    # Resource nodes: r1..r3, ports 5001..5003 (as in docker-compose)
    resource_nodes_env = os.environ.get(
        'RESOURCE_NODES',
        'r1:resource_r1:5001,r2:resource_r2:5002,r3:resource_r3:5003'
    )
    resource_nodes = {}
    for entry in resource_nodes_env.split(','):
        parts = entry.strip().split(':')
        r_id, host, rport = parts[0], parts[1], int(parts[2])
        resource_nodes[r_id] = (host, rport)

    coord = Coordinator(resource_nodes=resource_nodes)
    coord.serve(port=port)
