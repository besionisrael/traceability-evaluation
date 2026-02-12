"""
Directed Traceability Mechanism (M_D)

Enforces all constraints (local + global) using global state before recording.
Guarantees IVR = 0 by construction (Theorem 5.1).
"""
from typing import List, Tuple
import time
from core import SystemState, Interaction, evaluate_all_constraints


class DirectedMechanism:
    """
    Implements M_D as defined in Definition 3.10.
    
    A traceability mechanism M_D ensures directed traceability if:
    
    1. Global validation a priori:
       ∀u_t ∈ U_all:
           If Conf(s_t, u_t) = 1
           Then Record(u_t) ∧ s_{t+1} ← δ(s_t, u_t)
           Else Reject(u_t) ∧ s_{t+1} ← s_t
    
    2. Compliance guarantee:
       ∀τ_D ∈ Traces(M_D), ∀i : Conf(s_i, u_i) = 1
    """
    
    def __init__(self):
        self.trace: List[Tuple[SystemState, Interaction]] = []
        self.rejected_count = 0
        self.total_attempts = 0
        self.latencies: List[float] = []  # Validation latencies in microseconds
    
    def process_interaction(self, state: SystemState, interaction: Interaction) -> SystemState:
        """
        Process an interaction using directed mechanism (Algorithm 1).
        
        Algorithm:
        Atomically:
            1. Acquire current global state
            2. Evaluate compliance Conf(s_t, u_t)
            3. If compliant: accept (record + update state)
               Else: reject (no changes)
        
        Args:
            state: Current system state
            interaction: Attempted interaction
        
        Returns:
            Updated state (or unchanged if rejected)
        """
        self.total_attempts += 1
        
        # Measure validation latency
        start_time = time.perf_counter()
        
        # Step 1: Acquire current global state (already have it)
        s_current = state
        
        # Step 2: Evaluate compliance using ALL constraints
        is_compliant = evaluate_all_constraints(s_current, interaction)
        
        # Record latency
        end_time = time.perf_counter()
        latency_us = (end_time - start_time) * 1e6  # Convert to microseconds
        self.latencies.append(latency_us)
        
        # Step 3: Conditional admission
        if is_compliant:
            # Accept: record and apply transition
            self.trace.append((s_current.copy(), interaction))
            new_state = self._apply_transition(s_current, interaction)
            return new_state
        else:
            # Reject: no changes
            self.rejected_count += 1
            return s_current
    
    def _apply_transition(self, state: SystemState, interaction: Interaction) -> SystemState:
        """Apply state transition δ(s_t, u_t)."""
        new_state = state.copy()
        
        if interaction.action == 'acquire':
            new_state.locks[interaction.resource].add(interaction.agent)
        elif interaction.action == 'release':
            new_state.locks[interaction.resource].discard(interaction.agent)
        
        return new_state
    
    def compute_ivr(self) -> float:
        """
        Compute Invariant Violation Rate (IVR).
        
        For M_D, IVR = 0 by construction (Theorem 5.1).
        
        Returns:
            Violation rate (should always be 0.0)
        """
        if len(self.trace) == 0:
            return 0.0
        
        violations = 0
        for state, interaction in self.trace:
            if not evaluate_all_constraints(state, interaction):
                violations += 1
        
        # Should always be 0 for M_D
        return violations / len(self.trace)
    
    def compute_eg(self) -> float:
        """
        Compute Enforcement Gap (EG).
        
        For M_D, EG > 0 because non-compliant interactions are rejected.
        
        Returns:
            Rejection rate in [0, 1]
        """
        if self.total_attempts == 0:
            return 0.0
        return self.rejected_count / self.total_attempts
    
    def get_trace_length(self) -> int:
        """Return number of recorded interactions."""
        return len(self.trace)
    
    def get_average_latency(self) -> float:
        """
        Compute average validation latency.
        
        Returns:
            Average latency in microseconds
        """
        if len(self.latencies) == 0:
            return 0.0
        return sum(self.latencies) / len(self.latencies)
    
    def reset(self):
        """Reset mechanism state for new run."""
        self.trace = []
        self.rejected_count = 0
        self.total_attempts = 0
        self.latencies = []
