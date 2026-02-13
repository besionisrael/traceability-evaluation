#!/usr/bin/env python3
"""
Resource Node — TCP server managing one resource.

Handles three request types:
  GET_STATE   → returns current resource state (used by M_D coordinator)
  PROCESS_MP  → record unconditionally (M_P)
  PROCESS_ML  → validate locally then record (M_L)
  COMMIT      → state update from M_D coordinator after global validation
"""
import os
import sys
import json
import socket
import threading
import time
import logging
from typing import List, Dict

sys.path.insert(0, '/app')
from shared.models import ResourceState, Interaction, encode_msg, decode_msg
from shared.constraints import evaluate_local

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s')


class ResourceNode:
    def __init__(self, resource_id: str, agents: List[str]):
        self.resource_id = resource_id
        self.state = ResourceState(resource_id=resource_id)
        self.lock = threading.Lock()

        # Initialize permissions: all agents authorized by default
        for agent in agents:
            self.state.permissions[agent] = True

        # Trace: list of dicts {interaction, mechanism, admitted, timestamp_us}
        self.trace: List[dict] = []
        self.logger = logging.getLogger(f"Node-{resource_id}")

    # ── State management ─────────────────────────────────────────────────────

    def get_state_snapshot(self) -> dict:
        with self.lock:
            return self.state.to_dict()

    def apply_transition(self, interaction: Interaction):
        """Apply state transition (lock acquire/release)."""
        if interaction.action == 'acquire':
            self.state.locks.add(interaction.agent)
        elif interaction.action == 'release':
            self.state.locks.discard(interaction.agent)

    # ── Request handlers ─────────────────────────────────────────────────────

    def handle_get_state(self) -> dict:
        return {'ok': True, 'state': self.get_state_snapshot()}

    def handle_process_mp(self, interaction: Interaction) -> dict:
        """M_P: record without any validation."""
        t0 = time.perf_counter()
        with self.lock:
            # IVR fix: store state snapshot at moment of recording
            self.trace.append({
                'interaction': interaction.to_dict(),
                'mechanism': 'M_P',
                'admitted': True,
                'state_snapshot': self.state.to_dict(),
            })
            self.apply_transition(interaction)
        latency_us = (time.perf_counter() - t0) * 1e6
        return {'ok': True, 'admitted': True, 'latency_us': latency_us}

    def handle_process_ml(self, interaction: Interaction,
                          snapshot: dict = None) -> dict:
        """
        M_L: validate locally, record if valid.

        snapshot: if provided (sent by orchestrator), validation uses this
                  frozen state instead of live state — correctly simulates
                  concurrent agents all reading the same state at timestep t.
                  Conforms to Definition M_L: C_i(s^a_local(t), u_t).
        """
        t0 = time.perf_counter()
        with self.lock:
            if snapshot is not None:
                # Use orchestrator-provided snapshot for validation (concurrent read)
                validation_state = ResourceState.from_dict(snapshot)
            else:
                validation_state = self.state

            admitted = evaluate_local(validation_state, interaction)
            # IVR fix: store the snapshot used for validation
            self.trace.append({
                'interaction': interaction.to_dict(),
                'mechanism': 'M_L',
                'admitted': admitted,
                'state_snapshot': validation_state.to_dict(),
            })
            if admitted:
                self.apply_transition(interaction)
        latency_us = (time.perf_counter() - t0) * 1e6
        return {'ok': True, 'admitted': admitted, 'latency_us': latency_us}

    def handle_commit(self, interaction: Interaction, admitted: bool,
                      state_snapshot: dict = None) -> dict:
        """
        M_D: coordinator has already validated globally.
        Apply state transition and record if admitted.
        state_snapshot: the global state used for validation (sent by coordinator).
        """
        with self.lock:
            self.trace.append({
                'interaction': interaction.to_dict(),
                'mechanism': 'M_D',
                'admitted': admitted,
                'state_snapshot': state_snapshot,
            })
            if admitted:
                self.apply_transition(interaction)
        return {'ok': True}

    def handle_get_trace(self) -> dict:
        with self.lock:
            return {'ok': True, 'trace': self.trace.copy()}

    def handle_reset(self, agents: List[str]) -> dict:
        with self.lock:
            self.state = ResourceState(resource_id=self.resource_id)
            for agent in agents:
                self.state.permissions[agent] = True
            self.trace = []
        return {'ok': True}

    # ── TCP dispatch ─────────────────────────────────────────────────────────

    def dispatch(self, msg: dict) -> dict:
        req_type = msg.get('type')
        try:
            if req_type == 'GET_STATE':
                return self.handle_get_state()
            elif req_type == 'PROCESS_MP':
                return self.handle_process_mp(Interaction.from_dict(msg['interaction']))
            elif req_type == 'PROCESS_ML':
                return self.handle_process_ml(
                    Interaction.from_dict(msg['interaction']),
                    snapshot=msg.get('snapshot')   # may be None for non-concurrent use
                )
            elif req_type == 'COMMIT':
                return self.handle_commit(
                    Interaction.from_dict(msg['interaction']),
                    msg['admitted'],
                    state_snapshot=msg.get('state_snapshot')
                )
            elif req_type == 'GET_TRACE':
                return self.handle_get_trace()
            elif req_type == 'RESET':
                return self.handle_reset(msg.get('agents', []))
            else:
                return {'ok': False, 'error': f'Unknown request type: {req_type}'}
        except Exception as e:
            self.logger.error(f"Error handling {req_type}: {e}")
            return {'ok': False, 'error': str(e)}

    # ── Server loop ───────────────────────────────────────────────────────────

    def serve(self, host: str = '0.0.0.0', port: int = 5000):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen(50)
        self.logger.info(f"Listening on {host}:{port}")

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
    resource_id = os.environ.get('RESOURCE_ID', 'r1')
    port = int(os.environ.get('PORT', 5000))
    agents_env = os.environ.get('AGENTS', 'a1,a2,a3,a4,a5')
    agents = [a.strip() for a in agents_env.split(',')]

    node = ResourceNode(resource_id=resource_id, agents=agents)
    node.serve(port=port)
