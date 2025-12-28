from copilot_server.agent.models import Plan
from copilot_server.models.user_settings import AutonomyLevel, RiskLevel


def should_auto_execute(plan: Plan, autonomy_level: AutonomyLevel) -> bool:
    """
    Decide if plan should auto-execute based on autonomy level and risk.

    Decision Matrix:
    ---------------
    L0 (READ_ONLY):       Never auto-execute (always propose)
    L1 (RECOMMENDATIONS): Auto-execute READ_ONLY only
    L2 (ASSISTED):        Auto-execute READ_ONLY + WRITE_LOW_RISK
    L3 (SUPERVISED):      Auto-execute everything (future)

    Args:
        plan: Execution plan with risk levels
        autonomy_level: User's autonomy level setting

    Returns:
        True if plan should auto-execute, False if approval needed
    """
    max_risk = plan.max_risk_level

    # L0: Never auto-execute
    if autonomy_level == AutonomyLevel.READ_ONLY:
        return False

    # L1: Auto-execute pure analysis (READ_ONLY)
    if autonomy_level == AutonomyLevel.RECOMMENDATIONS:
        return max_risk == RiskLevel.READ_ONLY

    # L2: Auto-execute low-risk writes
    if autonomy_level == AutonomyLevel.ASSISTED:
        return max_risk in [RiskLevel.READ_ONLY, RiskLevel.WRITE_LOW_RISK]

    # L3: Auto-execute everything (future feature)
    if autonomy_level == AutonomyLevel.SUPERVISED:
        return True

    # Default: safe behavior
    return False
