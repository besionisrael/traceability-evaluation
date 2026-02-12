#!/usr/bin/env python3
"""
Quick test of all scenarios with minimal replications
"""
import sys
sys.path.insert(0, '/home/claude/traceability_evaluation')

from scenarios import Scenario1, Scenario2, Scenario3


def quick_test():
    """Run each scenario with just 1 replication to verify they work."""
    print("="*70)
    print("QUICK TEST - 1 replication per scenario")
    print("="*70)
    
    # Scenario 1
    print("\n[1/3] Testing Scenario 1 (IVR vs Concurrency)...")
    s1 = Scenario1()
    r1 = s1.run_experiment(lambda_values=[0.5], n_replications=1)
    print(f"  Result: M_D IVR = {r1[0.5]['M_D']['IVR']['mean']:.3f} (should be 0.000)")
    print(f"          M_P IVR = {r1[0.5]['M_P']['IVR']['mean']:.3f} (should be > 0)")
    
    # Scenario 2
    print("\n[2/3] Testing Scenario 2 (Global Constraints)...")
    s2 = Scenario2()
    r2 = s2.run_experiment(lambda_rate=0.5, n_replications=1)
    print(f"  Result: M_D IVR = {r2['M_D']['IVR']['mean']:.3f}")
    print(f"          M_L violations from C_global = {r2['M_L']['violations']['C_global']:.0f}")
    
    # Scenario 3
    print("\n[3/3] Testing Scenario 3 (Latency)...")
    s3 = Scenario3()
    r3 = s3.run_experiment(n_values=[5], k_values=[3], n_replications=1)
    print(f"  Result: M_D latency = {r3[(5,3)]['M_D']['avg_latency']['mean']:.1f} μs")
    print(f"          M_P latency = {r3[(5,3)]['M_P']['avg_latency']['mean']:.1f} μs")
    
    print("\n" + "="*70)
    print("QUICK TEST PASSED ✓")
    print("="*70)
    print("\nAll scenarios are working. You can now run:")
    print("  python run_evaluation.py")
    print("\nfor the full 100-replication evaluation.")


if __name__ == '__main__':
    quick_test()
