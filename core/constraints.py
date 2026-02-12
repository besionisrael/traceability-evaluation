"""
Usage Constraints for Traceability Evaluation

Implements three constraint types:
1. C_excl: Mutual exclusivity (local)
2. C_auth: Authorization (local)
3. C_global: Global multi-resource constraint (global)
"""
from typing import Callable, Set
from core.state import SystemState, LocalView
from core.interaction import Interaction


# Type alias for constraint functions
ConstraintFunc = Callable[[SystemState, Interaction], bool]
LocalConstraintFunc = Callable[[LocalView, Interaction], bool]


def C_excl(state: SystemState, interaction: Interaction) -> bool:
    """
    Mutual exclusivity constraint (local).
    
    A resource can be held by at most one agent at a time.
    
    Formal definition (Example 4.1):
    C_excl(s_t, u_t) = true ⟺ (u_t.action = acquire ⟹ s_t.locks[u_t.r] = ∅)
    """
    if interaction.action == 'acquire':
        return len(state.locks[interaction.resource]) == 0
    return True


def C_excl_local(local_view: LocalView, interaction: Interaction) -> bool:
    """Local version of C_excl using only local view."""
    if interaction.action == 'acquire':
        return len(local_view.resource_locks) == 0
    return True


def C_auth(state: SystemState, interaction: Interaction) -> bool:
    """
    Authorization constraint (local).
    
    An agent must possess a valid authorization for the resource.
    
    Formal definition (Example 4.2):
    C_auth(s_t, u_t) = true ⟺ 
        (u_t.a, u_t.r) ∈ s_t.permissions ∧ s_t.permissions[u_t.a, u_t.r].valid = true
    """
    key = (interaction.agent, interaction.resource)
    if key not in state.permissions:
        return False
    return state.permissions[key].is_valid_at(state.time)


def C_auth_local(local_view: LocalView, interaction: Interaction) -> bool:
    """Local version of C_auth using only local view."""
    if local_view.permission is None:
        return False
    return local_view.permission.valid


def C_global(state: SystemState, interaction: Interaction, 
             R_subset: Set[str] = None, K_max: int = 2) -> bool:
    """
    Global multi-resource constraint (global).
    
    At most K_max agents can simultaneously hold locks on resources in R_subset.
    
    Formal definition (Example 4.3):
    C_global(s_t, u_t) = true ⟺
        (u_t.action = acquire ∧ u_t.r ∈ R_subset) ⟹
        |{a ∈ A : ∃r' ∈ R_subset, a ∈ s_t.locks[r']}| < K_max
    
    Args:
        state: Global system state
        interaction: Attempted interaction
        R_subset: Set of monitored resources (default: {'r1', 'r2'})
        K_max: Maximum number of concurrent holders (default: 2)
    """
    if R_subset is None:
        R_subset = {'r1', 'r2'}
    
    if interaction.action == 'acquire' and interaction.resource in R_subset:
        # Count agents currently holding locks on any resource in R_subset
        agents_with_locks = set()
        for res in R_subset:
            agents_with_locks.update(state.locks[res])
        
        # Check if adding this agent would exceed K_max
        return len(agents_with_locks) < K_max
    
    return True


def evaluate_all_constraints(state: SystemState, interaction: Interaction,
                            constraints: list = None) -> bool:
    """
    Evaluate global compliance function Conf(s_t, u_t).
    
    Conf(s_t, u_t) = 1 ⟺ ∀C_i ∈ C : C_i(s_t, u_t) = true
    
    Args:
        state: Global system state
        interaction: Attempted interaction
        constraints: List of constraint functions (default: [C_excl, C_auth, C_global])
    
    Returns:
        True if all constraints satisfied, False otherwise
    """
    if constraints is None:
        constraints = [C_excl, C_auth, C_global]
    
    for constraint in constraints:
        if not constraint(state, interaction):
            return False
    
    return True


def evaluate_local_constraints(local_view: LocalView, interaction: Interaction) -> bool:
    """
    Evaluate only local constraints using agent's local view.
    
    Used by M_L (locally-validated mechanism).
    Can only evaluate C_excl and C_auth, not C_global.
    """
    if not C_excl_local(local_view, interaction):
        return False
    if not C_auth_local(local_view, interaction):
        return False
    return True
