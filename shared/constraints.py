"""
Constraint definitions — distributed version.

C_excl and C_auth operate on a single ResourceState (local).
C_global operates on the aggregated state from all resource nodes.
"""
from typing import Dict
from shared.models import ResourceState, Interaction


# ─── Local constraints (evaluated on target resource node) ───────────────────

def C_excl(resource_state: ResourceState, interaction: Interaction) -> bool:
    """Resource can be held by at most one agent at a time."""
    if interaction.action == 'acquire':
        return len(resource_state.locks) == 0
    return True


def C_auth(resource_state: ResourceState, interaction: Interaction) -> bool:
    """Agent must have a valid permission for the resource."""
    return resource_state.permissions.get(interaction.agent, False)


# ─── Global constraint (evaluated on aggregated state from all nodes) ─────────

R_SUBSET = {'r1', 'r2'}
K_MAX = 2


def C_global(all_states: Dict[str, ResourceState], interaction: Interaction) -> bool:
    """
    At most K_MAX agents can simultaneously hold locks on resources in R_SUBSET.
    Requires global state (aggregated from all resource nodes).
    """
    if interaction.action == 'acquire' and interaction.resource in R_SUBSET:
        agents_with_locks = set()
        for res_id in R_SUBSET:
            if res_id in all_states:
                agents_with_locks.update(all_states[res_id].locks)
        return len(agents_with_locks) < K_MAX
    return True


# ─── Composite evaluators ─────────────────────────────────────────────────────

def evaluate_local(resource_state: ResourceState, interaction: Interaction) -> bool:
    """M_L: evaluate only local constraints on the target resource node."""
    return C_excl(resource_state, interaction) and C_auth(resource_state, interaction)


def evaluate_global(all_states: Dict[str, ResourceState], interaction: Interaction) -> bool:
    """M_D: evaluate all constraints using aggregated global state."""
    target = all_states.get(interaction.resource)
    if target is None:
        return False
    if not C_excl(target, interaction):
        return False
    if not C_auth(target, interaction):
        return False
    if not C_global(all_states, interaction):
        return False
    return True
