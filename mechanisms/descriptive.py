"""
Descriptive Traceability Mechanism (M_P)

Records all interactions without prior validation.
Validation occurs after-the-fact during trace analysis.
"""
from typing import List, Tuple
from core import SystemState, Interaction, evaluate_all_constraints


class DescriptiveMechanism:
    """
    Implements M_P as defined in Definition 3.7.
    
    A traceability mechanism M_P is descriptive if it records all interactions
    attempted by agents, independently of their compliance with constraints.
    
    ∀u ∈ U_all : u is recorded in τ
    """
    
    def __init__(self):
        self.trace: List[Tuple[SystemState, Interaction]] = []
        self.rejected_count = 0
        self.total_attempts = 0
    
    def process_interaction(self, state: SystemState, interaction: Interaction) -> SystemState:
        """
        Process an interaction using descriptive mechanism.
        
        Algorithm:
        1. Record immediately without validation
        2. Apply state transition
        3. Return new state
        
        Args:
            state: Current system state
            interaction: Attempted interaction
        
        Returns:
            Updated state
        """
        self.total_attempts += 1
        
        # Step 1: Record immediately (no validation)
        self.trace.append((state.copy(), interaction))
        
        # Step 2: Apply state transition
        new_state = self._apply_transition(state, interaction)
        
        return new_state
    
    def _apply_transition(self, state: SystemState, interaction: Interaction) -> SystemState:
        """
        Apply state transition δ(s_t, u_t).
        
        For 'acquire': add agent to resource's lock set
        For 'release': remove agent from resource's lock set
        """
        new_state = state.copy()
        
        if interaction.action == 'acquire':
            new_state.locks[interaction.resource].add(interaction.agent)
        elif interaction.action == 'release':
            new_state.locks[interaction.resource].discard(interaction.agent)
        
        return new_state
    
    def compute_ivr(self) -> float:
        """
        Compute Invariant Violation Rate (IVR).
        
        IVR(M) = |{(s_i, u_i) ∈ τ : Conf(s_i, u_i) = 0}| / |τ|
        
        Returns:
            Violation rate in [0, 1]
        """
        if len(self.trace) == 0:
            return 0.0
        
        violations = 0
        for state, interaction in self.trace:
            if not evaluate_all_constraints(state, interaction):
                violations += 1
        
        return violations / len(self.trace)
    
    def compute_eg(self) -> float:
        """
        Compute Enforcement Gap (EG).
        
        EG = (Number of rejected attempts) / (Total attempts)
        
        For M_P, EG = 0 because nothing is rejected.
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
