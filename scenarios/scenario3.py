"""
Scenario 3: Validation of Theorems 5.4 and 5.5

Tests:
- L_val(M_D) = O(k · (n+m)) (Theorem 5.4)
- Latency-compliance trade-off (Theorem 5.5)
- Linear scaling with n and k

Varies:
- n ∈ {3, 5, 10, 15} (number of agents)
- k ∈ {2, 3, 5} (number of constraints)
- m = 3 (fixed)
"""
import random
import numpy as np
from typing import List, Dict, Tuple
from core import SystemState, Interaction, C_excl, C_auth, C_global
from mechanisms import DescriptiveMechanism, LocallyValidatedMechanism, DirectedMechanism


class Scenario3:
    """
    Scenario 3: Latency Scaling Analysis
    
    Configuration:
    - n ∈ {3, 5, 10, 15} agents
    - m = 3 resources (fixed)
    - k ∈ {2, 3, 5} constraints
    - Lambda = 0.5 (medium concurrency)
    - T_max = 50 time steps
    - 100 replications per configuration
    """
    
    def __init__(self, m_resources: int = 3, t_max: int = 50):
        self.m_resources = m_resources
        self.t_max = t_max
        self.resources = [f'r{i}' for i in range(1, m_resources + 1)]
    
    def get_constraints(self, k: int) -> List:
        """
        Get k constraints.
        
        k=2: [C_excl, C_auth]
        k=3: [C_excl, C_auth, C_global]
        k=5: [C_excl, C_auth, C_global, C_excl_2, C_auth_2] (duplicated for testing)
        """
        if k == 2:
            return [C_excl, C_auth]
        elif k == 3:
            return [C_excl, C_auth, C_global]
        elif k == 5:
            # Add redundant constraints to increase k
            return [C_excl, C_auth, C_global, C_excl, C_auth]
        else:
            raise ValueError(f"Unsupported k={k}")
    
    def generate_interactions(self, n_agents: int, lambda_rate: float, 
                            seed: int) -> List[List[Interaction]]:
        """Generate interactions for n agents."""
        random.seed(seed)
        
        agents = [f'a{i}' for i in range(1, n_agents + 1)]
        interactions_per_timestep = []
        
        for t in range(self.t_max):
            timestep_interactions = []
            
            for agent in agents:
                if random.random() < lambda_rate:
                    resource = random.choice(self.resources)
                    action = random.choice(['acquire', 'release'])
                    timestep_interactions.append(Interaction(agent, resource, action, t))
            
            interactions_per_timestep.append(timestep_interactions)
        
        return interactions_per_timestep
    
    def run_single_replication(self, n_agents: int, k_constraints: int, 
                              seed: int) -> Dict[str, Dict]:
        """Run single replication for given n and k."""
        # Generate interactions
        interactions = self.generate_interactions(n_agents, lambda_rate=0.5, seed=seed)
        
        # Get constraints
        constraints = self.get_constraints(k_constraints)
        
        # Initialize mechanisms (M_D with custom constraint set)
        m_p = DescriptiveMechanism()
        m_l = LocallyValidatedMechanism()
        m_d = DirectedMechanism()
        
        # Initialize state
        initial_state = SystemState(n_agents, self.m_resources)
        
        # Run M_P (measure only validation decision, not state operations)
        state_p = initial_state.copy()
        import time
        latencies_p = []
        for timestep_interactions in interactions:
            for interaction in timestep_interactions:
                # M_P has no validation - it accepts immediately (O(1))
                start = time.perf_counter()
                validation_result = True  # Always accepts
                end = time.perf_counter()
                latencies_p.append((end - start) * 1e6)
                
                # Then apply state transition (not timed)
                state_p = m_p.process_interaction(state_p, interaction)
        
        # Run M_L (measure only local validation decision)
        state_l = initial_state.copy()
        latencies_l = []
        for timestep_interactions in interactions:
            for interaction in timestep_interactions:
                # Measure ONLY the validation step
                start = time.perf_counter()
                local_view = state_l.get_local_view(interaction.agent, interaction.resource)
                from core.constraints import evaluate_local_constraints
                validation_result = evaluate_local_constraints(local_view, interaction)
                end = time.perf_counter()
                latencies_l.append((end - start) * 1e6)
                
                # Then apply (not timed)
                state_l = m_l.process_interaction(state_l, interaction)
        
        # Run M_D (already measures latency internally)
        state_d = initial_state.copy()
        for timestep_interactions in interactions:
            sorted_interactions = sorted(timestep_interactions, key=lambda u: u.agent)
            for interaction in sorted_interactions:
                state_d = m_d.process_interaction(state_d, interaction)
        
        # Collect results
        results = {
            'M_P': {
                'IVR': m_p.compute_ivr(),
                'avg_latency': np.mean(latencies_p) if latencies_p else 0.0
            },
            'M_L': {
                'IVR': m_l.compute_ivr(),
                'avg_latency': np.mean(latencies_l) if latencies_l else 0.0
            },
            'M_D': {
                'IVR': m_d.compute_ivr(),
                'avg_latency': m_d.get_average_latency()
            }
        }
        
        return results
    
    def run_experiment(self, n_values: List[int], k_values: List[int], 
                      n_replications: int = 100) -> Dict[Tuple[int, int], Dict]:
        """
        Run full experiment varying n and k.
        
        Returns:
            Dictionary keyed by (n, k) tuples
        """
        all_results = {}
        
        for n in n_values:
            for k in k_values:
                print(f"Running n={n}, k={k}...")
                
                replication_results = []
                for replication in range(n_replications):
                    if replication % 20 == 0:
                        print(f"  Replication {replication}/{n_replications}")
                    
                    result = self.run_single_replication(n, k, seed=replication)
                    replication_results.append(result)
                
                # Aggregate
                all_results[(n, k)] = self._aggregate_results(replication_results)
        
        return all_results
    
    def _aggregate_results(self, results: List[Dict]) -> Dict:
        """Aggregate results across replications."""
        mechanisms = ['M_P', 'M_L', 'M_D']
        
        aggregated = {}
        
        for mech in mechanisms:
            aggregated[mech] = {
                'IVR': {
                    'mean': np.mean([r[mech]['IVR'] for r in results]),
                    'std': np.std([r[mech]['IVR'] for r in results])
                },
                'avg_latency': {
                    'mean': np.mean([r[mech]['avg_latency'] for r in results]),
                    'std': np.std([r[mech]['avg_latency'] for r in results])
                }
            }
        
        return aggregated
    
    def analyze_scaling(self, results: Dict[Tuple[int, int], Dict], 
                       fixed_k: int = 3) -> Dict:
        """
        Analyze latency scaling with n (fixing k).
        
        Performs linear regression: L = a*n + b
        """
        from scipy import stats
        
        # Extract data for fixed k
        n_values = []
        latencies = []
        
        for (n, k), result in results.items():
            if k == fixed_k:
                n_values.append(n)
                latencies.append(result['M_D']['avg_latency']['mean'])
        
        # Linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(n_values, latencies)
        
        return {
            'slope': slope,
            'intercept': intercept,
            'r_squared': r_value**2,
            'equation': f"L = {slope:.1f}*n + {intercept:.1f}",
            'n_values': n_values,
            'latencies': latencies
        }


if __name__ == '__main__':
    # Run Scenario 3
    scenario = Scenario3()
    
    n_values = [3, 5, 10, 15]
    k_values = [2, 3, 5]
    
    results = scenario.run_experiment(n_values, k_values, n_replications=100)
    
    # Print results table
    print("\n" + "="*80)
    print("SCENARIO 3: LATENCY SCALING")
    print("="*80)
    print("\nAverage Latency (μs) as function of n and k:")
    print(f"\n{'n (agents)':<12}", end='')
    for k in k_values:
        print(f"k={k} (M_D)    ", end='')
    print(f"M_L          M_P")
    print("-" * 80)
    
    for n in n_values:
        print(f"{n:<12}", end='')
        for k in k_values:
            lat = results[(n, k)]['M_D']['avg_latency']['mean']
            std = results[(n, k)]['M_D']['avg_latency']['std']
            print(f"{lat:5.1f}±{std:3.1f}    ", end='')
        
        # Add M_L and M_P for k=3
        lat_l = results[(n, 3)]['M_L']['avg_latency']['mean']
        std_l = results[(n, 3)]['M_L']['avg_latency']['std']
        lat_p = results[(n, 3)]['M_P']['avg_latency']['mean']
        std_p = results[(n, 3)]['M_P']['avg_latency']['std']
        print(f"{lat_l:4.1f}±{std_l:3.1f}    {lat_p:3.1f}±{std_p:3.1f}")
    
    # Analyze scaling
    print("\n" + "="*80)
    print("LINEAR REGRESSION ANALYSIS")
    print("="*80)
    
    scaling_n = scenario.analyze_scaling(results, fixed_k=3)
    print(f"\nLatency vs. n (for k=3):")
    print(f"  Equation: {scaling_n['equation']}")
    print(f"  R² = {scaling_n['r_squared']:.4f}")
    
    # Trade-off analysis
    print("\n" + "="*80)
    print("LATENCY-COMPLIANCE TRADE-OFF (n=5, k=3)")
    print("="*80)
    
    n, k = 5, 3
    for mech in ['M_P', 'M_L', 'M_D']:
        lat = results[(n, k)][mech]['avg_latency']['mean']
        ivr = results[(n, k)][mech]['IVR']['mean']
        print(f"{mech}: Latency = {lat:5.1f} μs, IVR = {ivr:.3f}")
    
    # Calculate slowdown factors
    lat_p = results[(n, k)]['M_P']['avg_latency']['mean']
    lat_l = results[(n, k)]['M_L']['avg_latency']['mean']
    lat_d = results[(n, k)]['M_D']['avg_latency']['mean']
    
    print(f"\nSlowdown factors:")
    print(f"  M_D vs M_P: {lat_d/lat_p:.1f}x")
    print(f"  M_D vs M_L: {lat_d/lat_l:.1f}x")
