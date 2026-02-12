"""
Locally-Validated Traceability Mechanism (M_L)

Validates interactions using agent's local view before recording.
Can enforce local constraints (C_excl, C_auth) but not global constraints (C_global).
"""
from typing import List, Tuple
from core import SystemState, Interaction, evaluate_local_constraints, evaluate_all_constraints


class LocallyValidatedMechanism:
    """
    Implements M_L as defined in Definition 3.9.
    
    A mechanism M_L performs local validation if:
    ∀u_t = (a, r, α, t):
        If ∀C_i ∈ C_local : C_i(s^a_local(t), u_t) = true
        Then Record(u_t)
        Else Reject(u_t)
    """
    
    def __init__(self):
        self.trace: List[Tuple[SystemState, Interaction]] = []
        self.rejected_count = 0
        self.total_attempts = 0
    
    def process_interaction(self, state: SystemState, interaction: Interaction) -> SystemState:
        """
        Process an interaction using local validation.
        
        Algorithm:
        1. Get agent's local view
        2. Evaluate local constraints only
        3. If valid: record and apply transition
        4. If invalid: reject (no recording, no state change)
        
        Args:
            state: Current system state
            interaction: Attempted interaction
        
        Returns:
            Updated state (or unchanged if rejected)
        """
        self.total_attempts += 1
        
        # Step 1: Get agent's local view
        local_view = state.get_local_view(interaction.agent, interaction.resource)
        
        # Step 2: Evaluate local constraints using local view
        if evaluate_local_constraints(local_view, interaction):
            # Step 3: Accept - record and apply transition
            self.trace.append((state.copy(), interaction))
            new_state = self._apply_transition(state, interaction)
            return new_state
        else:
            # Step 4: Reject - no changes
            self.rejected_count += 1
            return state
    
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
        
        For M_L, IVR > 0 when global constraints are present (Theorem 5.3).
        
        Returns:
            Violation rate in [0, 1]
        """
        if len(self.trace) == 0:
            return 0.0
        
        violations = 0
        for state, interaction in self.trace:
            # Evaluate ALL constraints (including global ones)
            if not evaluate_all_constraints(state, interaction):
                violations += 1
        
        return violations / len(self.trace)
    
    def compute_eg(self) -> float:
        """
        Compute Enforcement Gap (EG).
        
        Returns:
            Rejection rate in [0, 1]
        """
        if self.total_attempts == 0:
            return 0.0
        return self.rejected_count / self.total_attempts
    
    def get_trace_length(self) -> int:
        """Return number of recorded interactions."""
        return len(self.trace)
    
    def reset(self):
        """Reset mechanism state for new run."""
        self.trace = []
        self.rejected_count = 0
        self.total_attempts = 0
