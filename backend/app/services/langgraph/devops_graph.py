import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from langgraph.graph import StateGraph

from dotenv import load_dotenv
import os
from pathlib import Path

# imports from sibling 'agent' folder
from backend.app.services.agent.devops_agent.devops_files.devops_types import DevOpsState

from backend.app.services.agent.devops_agent.devops_files.devops_types import refactor_devops
from backend.app.services.agent.common_files.transformer import transform_infra
from backend.app.services.agent.devops_agent.devops_files.metadata_logger import log_metadata
from backend.app.services.agent.devops_agent.devops_files.autoscaler import suggest_jenkins_optimizations
from backend.app.services.agent.devops_agent.devops_files.monitoring_tool import suggest_monitoring_integration
from backend.app.services.agent.devops_agent.devops_files.deployment_manager import recommend_deployment_strategy
from backend.app.services.agent.devops_agent.devops_files.terraform_validator import terraform_linter, terraform_plan_validator
from backend.app.services.agent.devops_agent.devops_files.terraform_cost_estimator import terraform_cost_estimator
from backend.app.services.agent.devops_agent.devops_files.github_pusher import push_to_github


load_dotenv(Path(__file__).resolve().parents[4] / ".env")


def devops_agent_main(infra_code: str, prompt_name: str = "Azure_DevOps_pipeline.j2", gh_token: str = None, gh_repo: str = None) -> DevOpsState:
    """
    Orchestrates the DevOps agent pipeline using LangGraph.

    Args:
        infra_code (str): The input infrastructure code (YAML, Terraform, etc.).
        prompt_name (str): The name of the prompt to use for transformation.

    Returns:
        DevOpsState: Final state after all nodes have run.
    """
    # Inject the prompt template into the transform function
    def transform_devops_with_prompt(state: DevOpsState) -> DevOpsState:
        return transform_infra(state, prompt_template=prompt_name)

    builder = StateGraph(DevOpsState)

    # Common node
    builder.add_node("transform_infra", transform_devops_with_prompt)

    if "terraform" in prompt_name.lower():
        # Terraform pipeline
        builder.add_node("terraform_linter", terraform_linter)
        builder.add_node("terraform_cost_estimator", terraform_cost_estimator)
        builder.add_node("terraform_plan_validator", terraform_plan_validator)
        builder.add_node("log_metadata", log_metadata)
        # builder.add_node("push_to_github", push_to_github)

        builder.set_entry_point("transform_infra")
        builder.add_edge("transform_infra", "terraform_linter")
        builder.add_edge("terraform_linter", "terraform_cost_estimator")
        builder.add_edge("terraform_cost_estimator", "terraform_plan_validator")
        builder.add_edge("terraform_plan_validator", "log_metadata")
        # builder.add_edge("log_metadata", "push_to_github")

    else:
        # Jenkins pipeline
        builder.add_node("refactor_devops", refactor_devops)
        builder.add_node("log_metadata", log_metadata)
        builder.add_node("autoscale", suggest_jenkins_optimizations)
        builder.add_node("add_monitoring", suggest_monitoring_integration)
        builder.add_node("deployment_strategy", recommend_deployment_strategy)
        # builder.add_node("push_to_github", push_to_github)

        builder.set_entry_point("transform_infra")
        builder.add_edge("transform_infra", "refactor_devops")
        builder.add_edge("refactor_devops", "log_metadata")
        builder.add_edge("log_metadata", "autoscale")
        builder.add_edge("autoscale", "add_monitoring")
        builder.add_edge("add_monitoring", "deployment_strategy")
        # builder.add_edge("deployment_strategy", "push_to_github")

    graph = builder.compile()
    return graph.invoke({
        "Devops_input": infra_code,
        "Devops_output": "",
        "gh_token": gh_token,
        "gh_repo": gh_repo
    })