from typing import Dict, Any, Optional
from copilot_server.agent.models import Plan, PlanStep
from copilot_server.models.user_settings import RiskLevel
from copilot_server.mcp import MCPClient


class PlanDetector:
    """Detects multi-tool plans from LLM responses."""

    PLAN_THRESHOLD = 3  # 3+ tools = plan

    def __init__(self, mcp_client: Optional[MCPClient] = None):
        """
        Initialize detector.

        Args:
            mcp_client: Optional MCP client for tool risk lookup
        """
        self.mcp_client = mcp_client
        self.tool_risks: Dict[str, RiskLevel] = {}

        if mcp_client:
            self._load_tool_risks()

    def _load_tool_risks(self):
        """Load tool risk levels from MCP tools."""
        tools = self.mcp_client.get_tools()
        for tool in tools:
            tool_name = tool.get("name", "")
            risk_str = tool.get("metadata", {}).get("risk_level", "CRITICAL")
            self.tool_risks[tool_name] = RiskLevel(risk_str)

    def is_plan(self, llm_response: Dict[str, Any]) -> bool:
        """
        Check if LLM response contains a multi-tool plan.

        Args:
            llm_response: Claude API response

        Returns:
            True if response has 3+ tool_use blocks
        """
        content = llm_response.get("content", [])
        tool_uses = [block for block in content if block.get("type") == "tool_use"]
        return len(tool_uses) >= self.PLAN_THRESHOLD

    def extract_plan(self, llm_response: Dict[str, Any], session_id: str) -> Plan:
        """
        Extract Plan object from LLM response.

        Args:
            llm_response: Claude API response with 3+ tool calls
            session_id: Session ID

        Returns:
            Plan object with steps and risk levels
        """
        content = llm_response.get("content", [])

        # Extract purpose from text blocks
        text_blocks = [block.get("text", "") for block in content if block.get("type") == "text"]
        purpose = " ".join(text_blocks).strip() or "Multi-tool workflow"

        # Extract tool steps
        tool_uses = [block for block in content if block.get("type") == "tool_use"]
        steps = []

        for tool_block in tool_uses:
            tool_name = tool_block.get("name", "")
            arguments = tool_block.get("input", {})

            # Get risk level (default to CRITICAL for unknown tools)
            risk_level = self.tool_risks.get(tool_name, RiskLevel.CRITICAL)

            steps.append(PlanStep(
                tool=tool_name,
                arguments=arguments,
                risk_level=risk_level
            ))

        # Calculate max risk level
        max_risk = max((step.risk_level for step in steps), default=RiskLevel.CRITICAL)

        return Plan(
            session_id=session_id,
            purpose=purpose,
            steps=steps,
            max_risk_level=max_risk
        )
