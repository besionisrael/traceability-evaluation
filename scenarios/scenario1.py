"""
Scenario 1: Validation of Theorems 5.1 and 5.2

Tests:
- M_D maintains IVR = 0 regardless of concurrency level (Theorem 5.1)
- M_P exhibits IVR > 0 that increases with concurrency (Theorem 5.2)
- M_L exhibits intermediate behavior

Active constraints: C_excl, C_auth
"""
import random
import numpy as np
from typing import List, Dict
from core import SystemState, Interaction
from mechanisms import DescriptiveMechanism, LocallyValidatedMechanism, DirectedMechanism


class Scenario1:
    """
    Scenario 1: IVR vs Concurrency Level
    
    Configuration:
    - n = 5 agents
    - m = 3 resources
    - T_max = 50 time steps
    - Lambda ∈ {0.3, 0.5, 0.7}
    - Constraints: C_excl, C_auth
    - 100 replications per configuration
    """
    
    def __init__(self, n_agents: int = 5, n_resources: int = 3, t_max: int = 50):
        self.n_agents = n_agents
        self.n_resources = n_resources
        self.t_max = t_max
        
        # Agent and resource IDs
        self.agents = [f'a{i}' for i in range(1, n_agents + 1)]
        self.resources = [f'r{i}' for i in range(1, n_resources + 1)]
    
    def generate_interactions(self, lambda_rate: float, seed: int) -> List[List[Interaction]]:
        """
        Generate interaction attempts for all time steps.
        
        Args:
            lambda_rate: Concurrency rate λ ∈ [0, 1]
            seed: Random seed for reproducibility
        
        Returns:
            List of interaction lists (one per time step)
        """
        random.seed(seed)
        
        interactions_per_timestep = []
        
        for t in range(self.t_max):
            timestep_interactions = []
            
            for agent in self.agents:
                if random.random() < lambda_rate:
                    # Agent attempts an interaction
                    resource = random.choice(self.resources)
                    action = random.choice(['acquire', 'release'])
                    timestep_interactions.append(Interaction(agent, resource, action, t))
            
            interactions_per_timestep.append(timestep_interactions)
        
        return interactions_per_timestep
    
    def run_single_replication(self, lambda_rate: float, seed: int) -> Dict[str, Dict]:
        """
        Run a single replication with all three mechanisms.
        
        Args:
            lambda_rate: Concurrency rate
            seed: Random seed
        
        Returns:
            Dictionary with results for each mechanism
        """
        # Generate interactions (same for all mechanisms)
        interactions = self.generate_interactions(lambda_rate, seed)
        
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
                    
                    # Apply transition to state_l (not snapshot)
                    if interaction.action == 'acquire':
                        state_l.locks[interaction.resource].add(interaction.agent)
                    elif interaction.action == 'release':
                        state_l.locks[interaction.resource].discard(interaction.agent)
                else:
                    # Reject
                    m_l.rejected_count += 1
                    m_l.total_attempts += 1
        
        # Run M_D (with serialization for concurrent interactions)
        state_d = initial_state.copy()
        for timestep_interactions in interactions:
            # Sort by agent ID for deterministic serialization
            sorted_interactions = sorted(timestep_interactions, key=lambda u: u.agent)
            for interaction in sorted_interactions:
                state_d = m_d.process_interaction(state_d, interaction)
        
        # Collect results
        results = {
            'M_P': {
                'IVR': m_p.compute_ivr(),
                'EG': m_p.compute_eg(),
                'trace_length': m_p.get_trace_length(),
                'total_attempts': m_p.total_attempts
            },
            'M_L': {
                'IVR': m_l.compute_ivr(),
                'EG': m_l.compute_eg(),
                'trace_length': m_l.get_trace_length(),
                'total_attempts': m_l.total_attempts
            },
            'M_D': {
                'IVR': m_d.compute_ivr(),
                'EG': m_d.compute_eg(),
                'trace_length': m_d.get_trace_length(),
                'total_attempts': m_d.total_attempts,
                'avg_latency': m_d.get_average_latency()
            }
        }
        
        return results
    
    def run_experiment(self, lambda_values: List[float], n_replications: int = 100) -> Dict:
        """
        Run full experiment for all concurrency levels.
        
        Args:
            lambda_values: List of concurrency rates to test
            n_replications: Number of replications per configuration
        
        Returns:
            Dictionary with aggregated results
        """
        all_results = {lambda_val: [] for lambda_val in lambda_values}
        
        for lambda_val in lambda_values:
            print(f"Running λ = {lambda_val}...")
            
            for replication in range(n_replications):
                if replication % 10 == 0:
                    print(f"  Replication {replication}/{n_replications}")
                
                result = self.run_single_replication(lambda_val, seed=replication)
                all_results[lambda_val].append(result)
        
        # Aggregate results
        aggregated = {}
        for lambda_val in lambda_values:
            aggregated[lambda_val] = self._aggregate_results(all_results[lambda_val])
        
        return aggregated
    
    def _aggregate_results(self, results: List[Dict]) -> Dict:
        """Aggregate results across replications (mean ± std)."""
        mechanisms = ['M_P', 'M_L', 'M_D']
        metrics = ['IVR', 'EG', 'trace_length']
        
        aggregated = {}
        
        for mech in mechanisms:
            aggregated[mech] = {}
            for metric in metrics:
                values = [r[mech][metric] for r in results]
                aggregated[mech][metric] = {
                    'mean': np.mean(values),
                    'std': np.std(values)
                }
            
            # Add latency for M_D
            if mech == 'M_D':
                latencies = [r[mech]['avg_latency'] for r in results]
                aggregated[mech]['avg_latency'] = {
                    'mean': np.mean(latencies),
                    'std': np.std(latencies)
                }
        
        return aggregated


if __name__ == '__main__':
    # Run Scenario 1
    scenario = Scenario1()
    
    lambda_values = [0.3, 0.5, 0.7]
    results = scenario.run_experiment(lambda_values, n_replications=100)
    
    # Print results
    print("\n" + "="*80)
    print("SCENARIO 1: IVR vs CONCURRENCY LEVEL")
    print("="*80)
    
    for lambda_val in lambda_values:
        print(f"\nλ = {lambda_val}:")
        for mech in ['M_P', 'M_L', 'M_D']:
            ivr = results[lambda_val][mech]['IVR']
            print(f"  {mech}: IVR = {ivr['mean']:.3f} ± {ivr['std']:.3f}")
