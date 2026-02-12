"""
Interaction representation for traceability evaluation
"""
from dataclasses import dataclass
from typing import Literal


@dataclass
class Interaction:
    """
    Represents an interaction attempt as defined in Definition 3.4.
    
    An interaction is a quadruplet: u_t = (a, r, α, t)
    where:
        a ∈ A: initiating agent
        r ∈ R: targeted resource
        α ∈ U: attempted action type
        t ∈ T: attempt instant
    """
    agent: str
    resource: str
    action: Literal['acquire', 'release']
    time: int
    
    def __repr__(self):
        return f"({self.agent}, {self.resource}, {self.action}, t={self.time})"
    
    def __str__(self):
        return f"{self.agent}.{self.action}({self.resource})"
