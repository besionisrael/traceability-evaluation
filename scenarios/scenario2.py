"""
Scenario 2: Validation of Theorem 5.3

Tests:
- M_L fails to enforce C_global despite successful local validation
- M_D maintains IVR = 0 even with global constraints
- Violations in M_L are primarily due to C_global

Active constraints: C_excl, C_auth, C_global
Configuration: Orchestrated scenario with 3 agents attempting R_subset = {r1, r2}
"""
import random
import numpy as np
from typing import List, Dict
from core import SystemState, Interaction, C_excl, C_auth, C_global
from mechanisms import DescriptiveMechanism, LocallyValidatedMechanism, DirectedMechanism


class Scenario2:
    """
    Scenario 2: Global Constraint Enforcement
    
    Configuration:
    - n = 5 agents
    - m = 3 resources
    - T_max = 50 time steps
    - Lambda = 0.5 (medium concurrency)
    - Constraints: C_excl, C_auth, C_global
    - C_global: max 2 agents on {r1, r2}
    - 100 replications
    """
    
    def __init__(self, n_agents: int = 5, n_resources: int = 3, t_max: int = 50):
        self.n_agents = n_agents
        self.n_resources = n_resources
        self.t_max = t_max
        
        self.agents = [f'a{i}' for i in range(1, n_agents + 1)]
        self.resources = [f'r{i}' for i in range(1, n_resources + 1)]
        
        # Global constraint parameters
        self.R_subset = {'r1', 'r2'}
        self.K_max = 2
    
    def generate_interactions(self, lambda_rate: float, seed: int, 
                            force_global_conflict: bool = True) -> List[List[Interaction]]:
        """
        Generate interactions with optional orchestrated global constraint conflicts.
        
        Args:
            lambda_rate: Concurrency rate
            seed: Random seed
            force_global_conflict: If True, insert orchestrated conflicts for C_global
        
        Returns:
            List of interaction lists per timestep
        """
        random.seed(seed)
        
        interactions_per_timestep = []
        
        for t in range(self.t_max):
            timestep_interactions = []
            
            # Regular random interactions
            for agent in self.agents:
                if random.random() < lambda_rate:
                    resource = random.choice(self.resources)
                    action = random.choice(['acquire', 'release'])
                    timestep_interactions.append(Interaction(agent, resource, action, t))
            
            # Insert orchestrated conflict every 10 steps
            if force_global_conflict and t % 10 == 0:
                # Force 3 agents to simultaneously attempt r1 and r2
                # This should violate C_global (max 2 agents on {r1, r2})
                timestep_interactions.extend([
                    Interaction('a1', 'r1', 'acquire', t),
                    Interaction('a2', 'r2', 'acquire', t),
                    Interaction('a3', 'r1', 'acquire', t)  # Third agent - violates C_global
                ])
            
            interactions_per_timestep.append(timestep_interactions)
        
        return interactions_per_timestep
    
    def classify_violations(self, mechanism, state_trace_pairs) -> Dict[str, int]:
        """
        Classify violations by constraint type.
        
        Returns:
            Dictionary with counts for each constraint type
        """
        violations = {
            'C_excl': 0,
            'C_auth': 0,
            'C_global': 0,
            'total': 0
        }
        
        for state, interaction in state_trace_pairs:
            is_violated = False
            
            if not C_excl(state, interaction):
                violations['C_excl'] += 1
                is_violated = True
            
            if not C_auth(state, interaction):
                violations['C_auth'] += 1
                is_violated = True
            
            if not C_global(state, interaction, self.R_subset, self.K_max):
                violations['C_global'] += 1
                is_violated = True
            
            if is_violated:
                violations['total'] += 1
        
        return violations
    
    def run_single_replication(self, lambda_rate: float, seed: int) -> Dict[str, Dict]:
        """Run single replication with global constraints."""
        # Generate interactions
        interactions = self.generate_interactions(lambda_rate, seed, force_global_conflict=True)
        
        # Initialize mechanisms
        m_p = DescriptiveMechanism()
        m_l = LocallyValidatedMechanism()
        m_d = DirectedMechanism()
        
        # Initialize state
        initial_state = SystemState(self.n_agents, self.n_resources)
        
        # Run M_P
        state_p = initial_state.copy()
        for timestep_interactions in interactions:
            for interaction in timestep_interactions:
                state_p = m_p.process_interaction(state_p, interaction)
        
        # Run M_L with concurrent race simulation
        # All agents see the SAME snapshot state at each timestep
        state_l = initial_state.copy()
        for timestep_interactions in interactions:
            # Snapshot: all agents evaluate against this frozen state
            snapshot = state_l.copy()
            
            for interaction in timestep_interactions:
                # Get local view from snapshot (NOT from state_l)
                local_view = snapshot.get_local_view(interaction.agent, interaction.resource)
                
                # Evaluate using local constraints only
                from core.constraints import evaluate_local_constraints
                if evaluate_local_constraints(local_view, interaction):
                    # Accept: record and update state_l progressively
                    m_l.trace.append((state_l.copy(), interaction))
                    m_l.total_attempts += 1
                    
                    # Apply transition to state_l
                    if interaction.action == 'acquire':
                        state_l.locks[interaction.resource].add(interaction.agent)
                    elif interaction.action == 'release':
                        state_l.locks[interaction.resource].discard(interaction.agent)
                else:
                    # Reject
                    m_l.rejected_count += 1
                    m_l.total_attempts += 1
        
        # Run M_D
        state_d = initial_state.copy()
        for timestep_interactions in interactions:
            sorted_interactions = sorted(timestep_interactions, key=lambda u: u.agent)
            for interaction in sorted_interactions:
                state_d = m_d.process_interaction(state_d, interaction)
        
        # Classify violations
        violations_p = self.classify_violations(m_p, m_p.trace)
        violations_l = self.classify_violations(m_l, m_l.trace)
        violations_d = self.classify_violations(m_d, m_d.trace)
        
        # Collect results
        results = {
            'M_P': {
                'IVR': m_p.compute_ivr(),
                'trace_length': m_p.get_trace_length(),
                'violations': violations_p
            },
            'M_L': {
                'IVR': m_l.compute_ivr(),
                'trace_length': m_l.get_trace_length(),
                'violations': violations_l
            },
            'M_D': {
                'IVR': m_d.compute_ivr(),
                'trace_length': m_d.get_trace_length(),
                'violations': violations_d
            }
        }
        
        return results
    
    def run_experiment(self, lambda_rate: float = 0.5, n_replications: int = 100) -> Dict:
        """Run full experiment."""
        all_results = []
        
        print(f"Running Scenario 2 with λ = {lambda_rate}...")
        
        for replication in range(n_replications):
            if replication % 10 == 0:
                print(f"  Replication {replication}/{n_replications}")
            
            result = self.run_single_replication(lambda_rate, seed=replication)
            all_results.append(result)
        
        # Aggregate
        return self._aggregate_results(all_results)
    
    def _aggregate_results(self, results: List[Dict]) -> Dict:
        """Aggregate results with violation breakdown."""
        mechanisms = ['M_P', 'M_L', 'M_D']
        
        aggregated = {}
        
        for mech in mechanisms:
            aggregated[mech] = {
                'IVR': {
                    'mean': np.mean([r[mech]['IVR'] for r in results]),
                    'std': np.std([r[mech]['IVR'] for r in results])
                },
                'trace_length': {
                    'mean': np.mean([r[mech]['trace_length'] for r in results]),
                    'std': np.std([r[mech]['trace_length'] for r in results])
                },
                'violations': {
                    'C_excl': np.mean([r[mech]['violations']['C_excl'] for r in results]),
                    'C_auth': np.mean([r[mech]['violations']['C_auth'] for r in results]),
                    'C_global': np.mean([r[mech]['violations']['C_global'] for r in results]),
                    'total': np.mean([r[mech]['violations']['total'] for r in results])
                }
            }
        
        return aggregated


if __name__ == '__main__':
    # Run Scenario 2
    scenario = Scenario2()
    results = scenario.run_experiment(lambda_rate=0.5, n_replications=100)
    
    # Print results
    print("\n" + "="*80)
    print("SCENARIO 2: GLOBAL CONSTRAINT ENFORCEMENT")
    print("="*80)
    
    for mech in ['M_P', 'M_L', 'M_D']:
        print(f"\n{mech}:")
        print(f"  IVR = {results[mech]['IVR']['mean']:.3f} ± {results[mech]['IVR']['std']:.3f}")
        print(f"  Violations:")
        print(f"    C_excl:   {results[mech]['violations']['C_excl']:.1f}")
        print(f"    C_auth:   {results[mech]['violations']['C_auth']:.1f}")
        print(f"    C_global: {results[mech]['violations']['C_global']:.1f}")
        print(f"    Total:    {results[mech]['violations']['total']:.1f}")
        
        # Calculate percentage
        if results[mech]['violations']['total'] > 0:
            pct_global = (results[mech]['violations']['C_global'] / 
                         results[mech]['violations']['total'] * 100)
            print(f"    C_global represents {pct_global:.1f}% of violations")
