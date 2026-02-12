"""
Generate figures for directed traceability paper.
Uses actual experimental results from evaluation.

Generates:
- Figure 1: IVR vs Concurrency Level
- Figure 2: Violation Breakdown by Constraint Type
- Figure 3: Latency Scaling Analysis
- Figure 4: Latency-Compliance Trade-off
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rcParams

# IEEE-style figure formatting
rcParams['font.family'] = 'serif'
rcParams['font.serif'] = ['Times New Roman']
rcParams['font.size'] = 10
rcParams['axes.labelsize'] = 10
rcParams['axes.titlesize'] = 11
rcParams['xtick.labelsize'] = 9
rcParams['ytick.labelsize'] = 9
rcParams['legend.fontsize'] = 9
rcParams['figure.titlesize'] = 11

# Data from actual experimental results
scenario1_data = {
    'lambda': [0.3, 0.5, 0.7],
    'M_D': [0.000, 0.000, 0.000],
    'M_L': [2.17, 3.63, 4.21],  # Percentages
    'M_P': [45.38, 46.93, 47.68]
}

scenario2_data = {
    'M_D': {'C_excl': 0, 'C_global': 0},
    'M_L': {'C_excl': 4.55, 'C_global': 4.07},
    'M_P': {'C_excl': 73.08, 'C_global': 54.76}
}

scenario3_scaling_n = {
    'n': [3, 5, 10, 15],
    'latency': [1.08, 1.08, 1.15, 2.24]  # k=3
}

scenario3_scaling_k = {
    'k': [2, 3, 5],
    'latency': [1.11, 1.08, 1.13]  # n=5
}

scenario3_tradeoff = {
    'M_P': {'latency': 0.12, 'IVR': 46.9},
    'M_L': {'latency': 1.67, 'IVR': 0.0},
    'M_D': {'latency': 1.08, 'IVR': 0.0}
}


def figure1_ivr_concurrency():
    """Figure 1: IVR vs Concurrency Level"""
    fig, ax = plt.subplots(figsize=(7, 4))
    
    lambda_vals = scenario1_data['lambda']
    
    # Plot lines
    ax.plot(lambda_vals, scenario1_data['M_D'], 'o-', 
            label='$M_D$ (Directed)', linewidth=2, markersize=8, color='#2E7D32')
    ax.plot(lambda_vals, scenario1_data['M_L'], 's-', 
            label='$M_L$ (Local)', linewidth=2, markersize=8, color='#1976D2')
    ax.plot(lambda_vals, scenario1_data['M_P'], '^-', 
            label='$M_P$ (Descriptive)', linewidth=2, markersize=8, color='#C62828')
    
    ax.set_xlabel('Concurrency rate $\\lambda$')
    ax.set_ylabel('Invariant Violation Rate (IVR) (%)')
    ax.set_title('Violation Rate as Function of Concurrency')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_xticks([0.3, 0.5, 0.7])
    ax.set_ylim(-2, 52)
    
    plt.tight_layout()
    plt.savefig('./figures/fig1_ivr_concurrency.pdf', dpi=300, bbox_inches='tight')
    plt.savefig('./figures/fig1_ivr_concurrency.png', dpi=300, bbox_inches='tight')
    print("✓ Figure 1 saved: fig1_ivr_concurrency.pdf/png")
    plt.close()


def figure2_violation_breakdown():
    """Figure 2: Violation Breakdown by Constraint Type"""
    fig, ax = plt.subplots(figsize=(7, 4))
    
    mechanisms = ['$M_D$', '$M_L$', '$M_P$']
    c_excl = [scenario2_data['M_D']['C_excl'], 
              scenario2_data['M_L']['C_excl'], 
              scenario2_data['M_P']['C_excl']]
    c_global = [scenario2_data['M_D']['C_global'], 
                scenario2_data['M_L']['C_global'], 
                scenario2_data['M_P']['C_global']]
    
    x = np.arange(len(mechanisms))
    width = 0.6
    
    # Stacked bars
    p1 = ax.bar(x, c_excl, width, label='$C_{\\text{excl}}$ violations', 
                color='#1976D2', alpha=0.8)
    p2 = ax.bar(x, c_global, width, bottom=c_excl, label='$C_{\\text{global}}$ violations',
                color='#D32F2F', alpha=0.8)
    
    ax.set_ylabel('Number of violations (average)')
    ax.set_title('Violation Breakdown by Constraint Type')
    ax.set_xticks(x)
    ax.set_xticklabels(mechanisms)
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3, linestyle='--', axis='y')
    
    # Add value labels on bars
    for i, (excl, glob) in enumerate(zip(c_excl, c_global)):
        if excl > 0:
            ax.text(i, excl/2, f'{excl:.1f}', ha='center', va='center', 
                   fontsize=8, fontweight='bold', color='white')
        if glob > 0:
            ax.text(i, excl + glob/2, f'{glob:.1f}', ha='center', va='center',
                   fontsize=8, fontweight='bold', color='white')
    
    plt.tight_layout()
    plt.savefig('./figures/fig2_violation_breakdown.pdf', dpi=300, bbox_inches='tight')
    plt.savefig('./figures/fig2_violation_breakdown.png', dpi=300, bbox_inches='tight')
    print("✓ Figure 2 saved: fig2_violation_breakdown.pdf/png")
    plt.close()


def figure3_latency_scaling():
    """Figure 3: Latency Scaling Analysis (2 subplots)"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    
    # Left subplot: Latency vs n (agents)
    n_vals = scenario3_scaling_n['n']
    latency_n = scenario3_scaling_n['latency']
    
    ax1.plot(n_vals, latency_n, 'o-', markersize=8, linewidth=2, color='#1976D2', label='Measured')
    
    # Linear regression
    coeffs = np.polyfit(n_vals, latency_n, 1)
    poly = np.poly1d(coeffs)
    n_fit = np.linspace(3, 15, 100)
    ax1.plot(n_fit, poly(n_fit), '--', color='#D32F2F', linewidth=1.5, 
            label=f'Linear fit: $L = {coeffs[0]:.2f}n + {coeffs[1]:.2f}$')
    
    # R^2
    residuals = latency_n - poly(n_vals)
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((latency_n - np.mean(latency_n))**2)
    r_squared = 1 - (ss_res / ss_tot)
    
    ax1.text(0.05, 0.95, f'$R^2 = {r_squared:.3f}$', transform=ax1.transAxes,
            fontsize=9, verticalalignment='top', bbox=dict(boxstyle='round', 
            facecolor='wheat', alpha=0.5))
    
    ax1.set_xlabel('Number of agents ($n$)')
    ax1.set_ylabel('Latency ($\\mu$s)')
    ax1.set_title('Latency vs. Agent Count ($k=3$)')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3, linestyle='--')
    
    # Right subplot: Latency vs k (constraints)
    k_vals = scenario3_scaling_k['k']
    latency_k = scenario3_scaling_k['latency']
    
    ax2.plot(k_vals, latency_k, 's-', markersize=8, linewidth=2, color='#1976D2', label='Measured')
    
    # Linear regression
    coeffs_k = np.polyfit(k_vals, latency_k, 1)
    poly_k = np.poly1d(coeffs_k)
    k_fit = np.linspace(2, 5, 100)
    ax2.plot(k_fit, poly_k(k_fit), '--', color='#D32F2F', linewidth=1.5,
            label=f'Linear fit: $L = {coeffs_k[0]:.2f}k + {coeffs_k[1]:.2f}$')
    
    # R^2
    residuals_k = latency_k - poly_k(k_vals)
    ss_res_k = np.sum(residuals_k**2)
    ss_tot_k = np.sum((latency_k - np.mean(latency_k))**2)
    r_squared_k = 1 - (ss_res_k / ss_tot_k)
    
    ax2.text(0.05, 0.95, f'$R^2 = {r_squared_k:.3f}$', transform=ax2.transAxes,
            fontsize=9, verticalalignment='top', bbox=dict(boxstyle='round',
            facecolor='wheat', alpha=0.5))
    
    ax2.set_xlabel('Number of constraints ($k$)')
    ax2.set_ylabel('Latency ($\\mu$s)')
    ax2.set_title('Latency vs. Constraint Count ($n=5$)')
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3, linestyle='--')
    ax2.set_xticks([2, 3, 4, 5])
    
    plt.tight_layout()
    plt.savefig('./figures/fig3_latency_scaling.pdf', dpi=300, bbox_inches='tight')
    plt.savefig('./figures/fig3_latency_scaling.png', dpi=300, bbox_inches='tight')
    print("✓ Figure 3 saved: fig3_latency_scaling.pdf/png")
    plt.close()


def figure4_tradeoff():
    """Figure 4: Latency-Compliance Trade-off"""
    fig, ax = plt.subplots(figsize=(7, 5))
    
    # Extract data
    mechanisms = ['M_P', 'M_L', 'M_D']
    latencies = [scenario3_tradeoff[m]['latency'] for m in mechanisms]
    ivrs = [scenario3_tradeoff[m]['IVR'] for m in mechanisms]
    colors = ['#C62828', '#1976D2', '#2E7D32']
    labels = ['$M_P$ (Descriptive)', '$M_L$ (Local)', '$M_D$ (Directed)']
    markers = ['^', 's', 'o']
    
    # Plot points
    for i, (lat, ivr, color, label, marker) in enumerate(zip(latencies, ivrs, colors, labels, markers)):
        ax.scatter(lat, ivr, s=200, color=color, label=label, marker=marker, 
                  edgecolors='black', linewidths=1.5, zorder=3)
        
        # Annotate
        if ivr > 0:
            ax.annotate(f'{lat:.2f} μs\n{ivr:.1f}%', (lat, ivr), 
                       xytext=(10, 10), textcoords='offset points',
                       fontsize=8, bbox=dict(boxstyle='round,pad=0.3', 
                       facecolor=color, alpha=0.3))
        else:
            ax.annotate(f'{lat:.2f} μs\n0%', (lat, ivr), 
                       xytext=(10, -15), textcoords='offset points',
                       fontsize=8, bbox=dict(boxstyle='round,pad=0.3',
                       facecolor=color, alpha=0.3))
    
    ax.set_xlabel('Validation Latency ($\\mu$s)')
    ax.set_ylabel('Invariant Violation Rate (IVR) (%)')
    ax.set_title('Latency-Compliance Trade-off ($n=5$, $k=3$)')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_xlim(-0.1, 2.0)
    ax.set_ylim(-5, 52)
    
    # Add Pareto frontier annotation
    ax.axhline(y=0, color='green', linestyle=':', linewidth=1, alpha=0.5)
    ax.text(1.5, 2, 'Zero violations', fontsize=8, color='green', style='italic')
    
    plt.tight_layout()
    plt.savefig('./figures/fig4_tradeoff.pdf', dpi=300, bbox_inches='tight')
    plt.savefig('./figures/fig4_tradeoff.png', dpi=300, bbox_inches='tight')
    print("✓ Figure 4 saved: fig4_tradeoff.pdf/png")
    plt.close()


def generate_all_figures():
    """Generate all 4 figures"""
    print("Generating figures for directed traceability paper...\n")
    
    figure1_ivr_concurrency()
    figure2_violation_breakdown()
    figure3_latency_scaling()
    figure4_tradeoff()
    
    print("\n✓ All figures generated successfully!")
    print("\nOutput location: ./figures/")
    print("Files generated:")
    print("  - fig1_ivr_concurrency.pdf/.png")
    print("  - fig2_violation_breakdown.pdf/.png")
    print("  - fig3_latency_scaling.pdf/.png")
    print("  - fig4_tradeoff.pdf/.png")


if __name__ == "__main__":
    generate_all_figures()