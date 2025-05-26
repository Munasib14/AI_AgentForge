from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
#from app.services.agent.common_files.push_to_github import  push_all_local_changes, PushPayload, push_to_github
import os
from pathlib import Path
from backend.app.services.langgraph.devops_graph import devops_agent_main
from backend.app.services.agent.devops_agent.devops_files.devops_types import DevOpsState
from backend.app.services.agent.devops_agent.devops_files.github_pusher import push_to_github

import base64
import requests
from dotenv import load_dotenv
from backend.app.services.agent.devops_agent.devops_files.logger_config import setup_logger

logger = setup_logger("DevOpsLogger") 

# import logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
GITHUB_TOKEN = os.getenv("GITHUB_PAT")  # Assuming your .env file has GITHUB_PAT=ghp_...
GITHUB_API_URL = "https://api.github.com"

# Initialize FastAPI
app = FastAPI()


# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup directories
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PROMPT_DIR = os.path.join(BASE_DIR, "app", "services", "agent",  "db_agent", "db_prompts")
WEB_PROMPT_DIR = os.path.join(BASE_DIR, "app", "services", "agent", "web_agent", "web_prompts")
TEST_PROMPT_DIR = os.path.join(BASE_DIR, "app", "services", "agent", "test_agent", "Playwright_prompts")
DEV_PROMPT_DIR = os.path.join(BASE_DIR, "app", "services", "agent", "devops_agent", "devops_prompts")

# Jinja2 Environment
env = Environment(
    loader=FileSystemLoader([DB_PROMPT_DIR, WEB_PROMPT_DIR,TEST_PROMPT_DIR,DEV_PROMPT_DIR]),
    auto_reload=True,
    cache_size=0,
)

# Models
class SQLRequest(BaseModel):
    sql_code: str
    prompt_name: str

class WebRequest(BaseModel):
    html_code: str
    prompt_name: str

class TestRequest(BaseModel):
    source_code: str
    prompt_name: str
    
class DevOpsRequest(BaseModel):
    infra_description: str
    prompt_name: str
    
    
class SharePayload(BaseModel):
    content: str
    githubUrl: str  # F
# Push to GitHub route
router = APIRouter()



# @router.post("/push-to-github/")
# async def push_to_github_route(payload: PushPayload):
#     try:
#         result = push_to_github(payload)
#         return {"message": "✅ Successfully pushed to GitHub!", "github_response": result}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"❌ Failed to push to GitHub: {str(e)}")

# # Route to push all local changes to GitHub
# @router.post("/push-all-local/")
# async def push_all_local_route():
#     result = push_all_local_changes()
#     return JSONResponse(content={"message": result})


# Mount the router into the app
app.include_router(router)

@app.get("/")
async def root():
    return {"message": "DB / Web / Test Agent FastAPI Server is running 🚀"}

# Add global cache variables
db_agent_fn = None
web_agent_fn = None
test_agent_fn = None
dev_agent_fn = None



@app.post("/run-db-agent/")
async def run_db_agent(request: SQLRequest):
    global db_agent_fn
    if db_agent_fn is None:
        from app.services.langgraph.db_graph import db_agent_main
        db_agent_fn = db_agent_main  # Cache it after first import

    prompt = request.prompt_name.strip() or "transform_identity.j2"
    result = db_agent_fn(request.sql_code, prompt_name=prompt)
    return {"result": result}

@app.post("/run-web-agent/")
async def run_web_agent(request: WebRequest):
    global web_agent_fn
    if web_agent_fn is None:
        from app.services.langgraph.web_graph import web_agent_main
        web_agent_fn = web_agent_main  # Cache it after first import

    prompt = request.prompt_name.strip() or "convert_asp_net_to_react.j2"
    result = web_agent_fn(request.html_code, prompt_name=prompt)
    return {"result": result}




@app.post("/run-test-agent/")
async def run_test_agent(request: TestRequest):
    print("Received payload:", request)
    global test_agent_fn
    if test_agent_fn is None:
        from app.services.langgraph.test_graph import test_agent_main
        test_agent_fn = test_agent_main  # Cache it after first import
    prompt = request.prompt_name.strip() or "Convert_ReactPage_to_Playwright.j2"
    # prompt = request.prompt_name.strip() or (
    # "Convert_ReactPage_to_Playwright.j2" if "React" in request.input_type else
    # "Convert_SeleniumTest_to_Playwright.j2" if "Selenium" in request.input_type else
    # "Convert_UserStory_to_PlaywrightFeature.j2")


    result = test_agent_fn(request.source_code, prompt_name=prompt)
    return {"result": result}



# @app.post("/run-devops-agent/")
# async def run_devops_agent(request: DevOpsRequest):
#     prompt = request.prompt_name.strip() or "devops_infra.j2"
#     result = devops_agent_main(request.infra_description, prompt_name=prompt)
#     return {"result": result}

@app.post("/run-devops-agent/")
async def run_devops_agent(request: DevOpsRequest):
    prompt = (request.prompt_name or "").strip() or "Azure_DevOps_pipeline.j2"

    # Load GitHub credentials from environment
    gh_token = os.getenv("GH_TOKEN")
    gh_repo = os.getenv("GH_REPO")  # e.g., "your-org/your-repo"

    if not gh_token or not gh_repo:
        logger.error("Missing GH_TOKEN or GH_REPO environment variable.")
        return {
            "result": None,
            "status": "Environment variables GH_TOKEN or GH_REPO are missing"
        }

    try:
        logger.info(f"Running DevOps agent with prompt: {prompt}")
        result = devops_agent_main(
            infra_code=request.infra_description,
            prompt_name=prompt,
            gh_token=gh_token,
            gh_repo=gh_repo
        )
    except Exception as e:
        logger.exception("Error during DevOps agent execution.")
        return {
            "result": None,
            "status": "Workflow generation failed",
            "error": str(e)
        }

    try:
        workflow_path = ".github/workflows/generated_pipeline.yml"
        logger.info(f"Pushing generated workflow to GitHub: {gh_repo}/{workflow_path}")

        state = DevOpsState(
            Devops_input=request.infra_description,  # ✅ Add this
            Devops_output=result["Devops_output"],
            gh_token=gh_token,
            gh_repo=gh_repo,
            logs=[]
            
        )

        push_to_github(state)

        return {
            "result": result,
            "status": "Workflow pushed to GitHub successfully"
        }

    except Exception as e:
        logger.exception("Failed to push workflow to GitHub.")
        return {
            "result": result,
            "status": "Workflow generation done, but push failed",
            "error": str(e)
        }



# @app.post("/run-dev-agent/")
# async def run_dev_agent(request: DevOpsRequest):
#     result = await devops_agent_main(request.infra_description, request.prompt_name)
#     return {"result": {"output": result}}



@app.post("/save-share/")
async def save_share(payload: SharePayload):
    try:
        if not GITHUB_TOKEN:
            raise HTTPException(status_code=500, detail="❌ GitHub token not set in environment.")

        content = payload.content
        github_url = payload.githubUrl.strip()

        if github_url.count("/") < 2:
            raise HTTPException(
                status_code=400,
                detail="❌ Invalid GitHub path. Format should be username/repo/path/file.txt"
            )

        username, repo, *path_parts = github_url.split("/")
        file_path = "/".join(path_parts)
        commit_message = f"Add {file_path} from chatbot share modal"

        api_url = f"{GITHUB_API_URL}/repos/{username}/{repo}/contents/{file_path}"

        # Encode content to base64 as required by GitHub API
        encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
        }

        # Check if file already exists to get its SHA (required for overwrite)
        response = requests.get(api_url, headers=headers)
        sha = response.json().get("sha") if response.status_code == 200 else None

        payload_data = {
            "message": commit_message,
            "content": encoded_content,
            "branch": "main",  # Change if needed
        }
        if sha:
            payload_data["sha"] = sha

        # Push the content
        push_response = requests.put(api_url, headers=headers, json=payload_data)

        if push_response.status_code in [200, 201]:
            return {"message": "✅ Content pushed to GitHub successfully"}
        else:
            return {
                "error": f"❌ Failed to push. Status: {push_response.status_code}",
                "details": push_response.json()
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Exception occurred: {str(e)}")






# @app.get("/get-prompt/")
# async def get_prompt(prompt_name: str, agent_type: str):

#     try:
#         # Lowercase and sanitize
#         prompt_name = prompt_name.strip()

#         # Define context
#         if agent_type == "Web Agent":
#             context = {"input_html": "-- Your ASP.NET code here"}
#         elif agent_type == "DB Agent":
#             context = {"input_sql": "-- Your SQL here"}
#         else:
#             raise ValueError(f"Unknown agent type: {agent_type}")

#         # Try to render prompt
#         template = env.get_template(prompt_name)
#         rendered = template.render(context)
#         return {"prompt_content": rendered}

#     except TemplateNotFound:
#         raise HTTPException(status_code=404, detail=f"Prompt '{prompt_name}' not found for agent type '{agent_type}'")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error rendering prompt: {str(e)}")

template_cache = {}

@app.get("/get-prompt/")
async def get_prompt(prompt_name: str, agent_type: str):
    global template_cache
    prompt_name = prompt_name.strip()

    cache_key = f"{agent_type}::{prompt_name}"
    if cache_key in template_cache:
        return {"prompt_content": template_cache[cache_key]}

    try:
        if agent_type == "Web Agent":
            context = {"input_html": "-- Your ASP.NET code here"}
        elif agent_type == "DB Agent":
            context = {"input_sql": "-- Your SQL here"}
        elif agent_type == "Test Agent":
            context = {"input_file": "-- React Code/API/Selenium TestCases"}
        elif agent_type == "DevOps Agent":
            context = {"infra_description": "-- jenkins / Terraform / ARM / YAML / Docker code here"}
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")

        template = env.get_template(prompt_name)
        rendered = template.render(context)
        template_cache[cache_key] = rendered
        return {"prompt_content": rendered}

    except TemplateNotFound:
        raise HTTPException(status_code=404, detail=f"Prompt '{prompt_name}' not found for agent type '{agent_type}'")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering prompt: {str(e)}")
