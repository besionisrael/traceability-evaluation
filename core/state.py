"""
System State Representation for Traceability Evaluation
"""
from typing import Dict, Set, Tuple
from copy import deepcopy


class SystemState:
    """
    Represents the state of the distributed system at a given time.
    
    Attributes:
        locks: Dict[resource_id, Set[agent_id]] - Current resource locks
        permissions: Dict[(agent_id, resource_id), PermissionRecord] - Authorization records
        time: int - Current time step
    """
    
    def __init__(self, num_agents: int, num_resources: int):
        self.locks: Dict[str, Set[str]] = {}
        self.permissions: Dict[Tuple[str, str], 'PermissionRecord'] = {}
        self.time: int = 0
        
        # Initialize empty locks for all resources
        for i in range(1, num_resources + 1):
            self.locks[f'r{i}'] = set()
        
        # Initialize permissions (all agents authorized on all resources initially)
        for i in range(1, num_agents + 1):
            for j in range(1, num_resources + 1):
                agent_id = f'a{i}'
                resource_id = f'r{j}'
                self.permissions[(agent_id, resource_id)] = PermissionRecord(valid=True)
    
    def copy(self) -> 'SystemState':
        """Create a deep copy of the state."""
        new_state = SystemState.__new__(SystemState)
        new_state.locks = deepcopy(self.locks)
        new_state.permissions = deepcopy(self.permissions)
        new_state.time = self.time
        return new_state
    
    def get_local_view(self, agent_id: str, resource_id: str) -> 'LocalView':
        """
        Get the local view accessible to an agent attempting to access a resource.
        
        Local view contains:
        - State of the targeted resource
        - Agent's own permissions for that resource
        """
        return LocalView(
            resource_locks=self.locks.get(resource_id, set()),
            permission=self.permissions.get((agent_id, resource_id), None),
            resource_id=resource_id
        )
    
    def __repr__(self):
        return f"State(t={self.time}, locks={self.locks})"


class PermissionRecord:
    """Represents an authorization record."""
    
    def __init__(self, valid: bool = True, time_window: Tuple[int, int] = None):
        self.valid = valid
        self.time_window = time_window  # (start_time, end_time) or None
    
    def is_valid_at(self, time: int) -> bool:
        """Check if permission is valid at given time."""
        if not self.valid:
            return False
        if self.time_window is None:
            return True
        start, end = self.time_window
        return start <= time <= end


class LocalView:
    """
    Represents an agent's local view of the system state.
    Contains only information directly accessible to that agent.
    """
    
    def __init__(self, resource_locks: Set[str], permission: PermissionRecord, resource_id: str):
        self.resource_locks = resource_locks
        self.permission = permission
        self.resource_id = resource_id
    
    def __repr__(self):
        return f"LocalView(resource={self.resource_id}, locks={self.resource_locks})"
