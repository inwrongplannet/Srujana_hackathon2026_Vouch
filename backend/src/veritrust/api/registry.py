"""In-memory records the API keeps for the life of the process (lost on restart).

Kept apart from the route modules so routers that never call the OR-Tools optimizer can share
them without importing it.
"""

from veritrust.models import CombinedAssessment, LoanApplication

applications: dict[str, LoanApplication] = {}
assessments: dict[str, CombinedAssessment] = {}
