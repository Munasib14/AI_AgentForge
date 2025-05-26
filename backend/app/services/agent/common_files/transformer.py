import os
from groq import Groq
from .prompt_engine import load_db_prompt,load_web_prompt,load_test_prompt,load_dev_prompt
from dotenv import load_dotenv
from pathlib import Path

from backend.app.services.agent.devops_agent.devops_files.devops_types import DevOpsState
load_dotenv(Path(__file__).resolve().parents[4] / ".env")



load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Function for transforming SQL
def transform_sql(state: dict, prompt_template="transform_identity.j2") -> dict:
    sql_text = state["input"]
    context = {"input_sql": sql_text}
    prompt = load_db_prompt(prompt_template, context)
    

    response = client.chat.completions.create(
        model="llama3-8b-8192",  # llama3-8b-8192 model from Groq
        messages=[{"role": "user", "content": prompt}]
    )

    transformed_sql = response.choices[0].message.content.strip()
    state["output"] += f"\n-- Transformed SQL --\n{transformed_sql}"
    return state

# Function for transforming ASP.NET or HTML to React (Web Agent)


def transform_web(state: dict, prompt_template="convert_asp_net_to_react.j2") -> dict:
    try:
        # Extract input HTML (ASP.NET code)
        html_code = state["input"]
        context = {"input_html": html_code}  # ⚠️ Ensure key matches template
        prompt = load_web_prompt(prompt_template, context)  # Load the refined prompt

        # Call the LLM model for transformation
        response = client.chat.completions.create(
            model="llama3-8b-8192",  # Ensure this model is capable of transformation
            messages=[{"role": "user", "content": prompt}]
        )

        # Extract the transformed React code
        transformed_code = response.choices[0].message.content.strip()

        # Ensure the state has an output key, and append the transformed code
        if "output" not in state:
            state["output"] = ""

        state["output"] += f"\n-- Transformed  Code --\n{transformed_code}"

    except Exception as e:
        state["output"] = f"⚠️ An error occurred during transformation: {str(e)}"
        # Log the error for debugging purposes
        print(f"Error in transform_web: {str(e)}")

    return state

def transform_test(state: dict, prompt_template="Convert_ReactPage_to_Playwright.j2") -> dict:
    try:
        # Extract input React code
        react_code = state["input"]
        context = {"input_react": react_code}  # ⚠️ Ensure key matches Jinja2 template
        prompt = load_test_prompt(prompt_template, context)  # Load the refined prompt

        # Call the LLM model for transformation
        response = client.chat.completions.create(
            model="llama3-8b-8192",  # Replace with actual model if different
            messages=[{"role": "user", "content": prompt}]
        )

        # Extract the transformed output (e.g., Playwright or test code)
        transformed_code = response.choices[0].message.content.strip()

        # Ensure the state has an output key, and append the transformed code
        if "output" not in state:
            state["output"] = ""

        state["output"] += f"\n-- Transformed Playwright Code --\n{transformed_code}"

    except Exception as e:
        state["output"] = f"⚠️ An error occurred during transformation: {str(e)}"
        print(f"Error in transform_web: {str(e)}")

    return state

def transform_infra(state: DevOpsState, prompt_template="Azure_DevOps_pipeline.j2") -> DevOpsState:
    """
    Uses Groq model to transform infrastructure code.
    """
    input_infra = state.Devops_input # Input infrastructure code (YAML, Terraform, etc.)
    
    # ✅ Wrap input_infra in a dictionary for Jinja2
    context = {"infra_description": input_infra}
    
    # Load prompt using jinja2 with proper context
    prompt = load_dev_prompt(prompt_template, context)
    

    # Call Groq model
    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",  # or another model Groq supports
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    

    transformed = response.choices[0].message.content.strip()
    state.Devops_output += f"\n# Transformed Infra\n{transformed}"
    return state

