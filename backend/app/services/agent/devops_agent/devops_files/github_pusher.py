import os
import re
import yaml
from github import Github
from github.GithubException import GithubException, UnknownObjectException
from dotenv import load_dotenv
from .devops_types import DevOpsState  # Adjust path if necessary
from .logger_config import setup_logger

logger = setup_logger("DevOpsLogger")

# Load environment variables
load_dotenv()


def clean_yaml_fences(yaml_string: str) -> str:
    yaml_string = yaml_string.strip()
    yaml_string = re.sub(r"^```(?:ya?ml)?\s*\n", "", yaml_string, flags=re.IGNORECASE)
    yaml_string = re.sub(r"\n```$", "", yaml_string)
    return yaml_string.strip()


def extract_yaml_block(markdown: str) -> str:
    match = re.search(r"```(?:ya?ml)?\s*\n(.*?)\n```", markdown, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else markdown.strip()


def fix_setup_java_distribution(yaml_content: str) -> str:
    try:
        data = yaml.safe_load(yaml_content)
        if not isinstance(data, dict) or 'jobs' not in data:
            return yaml_content

        for job in data['jobs'].values():
            if 'steps' not in job:
                continue
            for step in job['steps']:
                if isinstance(step, dict) and step.get('uses', '').startswith('actions/setup-java@'):
                    step.setdefault('with', {})
                    step['with'].setdefault('distribution', 'temurin')

        return yaml.dump(data, sort_keys=False)

    except yaml.YAMLError as e:
        logger.error(f"❌ YAML parsing failed: {e}")
        return yaml_content 
    
    
# def remove_java_gradle_steps(yaml_content: str) -> str:
#     data = yaml.safe_load(yaml_content)

#     if 'jobs' in data:
#         for job in data['jobs'].values():
#             job['steps'] = [
#                 step for step in job.get('steps', [])
#                 if not (
#                     'setup-java' in step.get('uses', '') or
#                     './gradlew' in step.get('run', '')
#                 )
#             ]
#     return yaml.dump(data, sort_keys=False)


def remove_java_gradle_steps(yaml_content: str) -> str:
    try:
        # Remove lines starting with '//' (which are invalid in YAML)
        cleaned_lines = []
        for line in yaml_content.splitlines():
            stripped = line.strip()
            if not stripped.startswith('//'):
                cleaned_lines.append(line)
        cleaned_yaml = '\n'.join(cleaned_lines)

        # Parse YAML content safely
        data = yaml.safe_load(cleaned_yaml)

        # Remove Java/Gradle steps if any
        if 'jobs' in data:
            for job in data['jobs'].values():
                job['steps'] = [
                    step for step in job.get('steps', [])
                    if not (
                        'setup-java' in step.get('uses', '') or
                        './gradlew' in step.get('run', '')
                    )
                ]

        # Return updated YAML as string
        return yaml.dump(data, sort_keys=False)

    except yaml.YAMLError as e:
        print(f"❌ YAML parsing failed: {e}")
        return None
    
    

def fix_sonar_scanner_commands(yaml_content: str) -> str:
    """
    Fix common issues with SonarScanner usage in GitHub Actions workflows.
    """
    try:
        # Replace ${{ secrets.VAR }} with $VAR
        yaml_content = re.sub(r'\${{\s*secrets\.([A-Z0-9_]+)\s*}}', r'$\1', yaml_content)
        
        # Replace ${VAR} with $VAR in shell run blocks
        yaml_content = re.sub(r'\$\{(\w+)\}', r'$\1', yaml_content)
        
        # Replace /s:$SONAR_TOKEN with /d:sonar.login
        yaml_content = re.sub(r'/s:\$\w+', r'/d:sonar.login="$SONAR_TOKEN"', yaml_content)
        
        # Fix /d:$SONAR_HOST_URL with correct sonar.host.url
        yaml_content = re.sub(r'/d:\$SONAR_HOST_URL', r'/d:sonar.host.url="$SONAR_HOST_URL"', yaml_content)
        
        # Clean newline issues
        yaml_content = re.sub(r'\\n\s*', r'\n', yaml_content)
        yaml_content = re.sub(r'\\\s*\n\s*', r' \\\n', yaml_content)

        # Optional: Replace multiline `run:` for Begin block with cleaner version
        sonar_begin_pattern = re.compile(
            r'(?<=- name: Begin SonarQube analysis\n  run: )(.*?)(?=\n\s*- name:|\Z)', re.DOTALL
        )

        fixed_sonar_begin = (
            '|\n'
            '    dotnet sonarscanner begin \\\n'
            '      /k:$SONAR_PROJECT_KEY \\\n'
            '      /n:$SONAR_PROJECT_NAME \\\n'
            '      /d:sonar.host.url="$SONAR_HOST_URL" \\\n'
            '      /d:sonar.login="$SONAR_TOKEN"'
        )

        yaml_content = sonar_begin_pattern.sub(fixed_sonar_begin, yaml_content)

        # Fix sonarscanner end command
        yaml_content = re.sub(
            r'dotnet sonarscanner end[^\n]*',
            'dotnet sonarscanner end /d:sonar.login="$SONAR_TOKEN"',
            yaml_content
        )

        return yaml_content

    except Exception as e:
        logger.error(f"❌ Error while fixing SonarScanner commands: {e}")
        return yaml_content



def remove_sonar_scanner_steps(yaml_content: str) -> str:
    """
    Removes steps related to SonarScanner from a GitHub Actions YAML file.
    """
    try:
        # Remove "Install SonarScanner" step
        yaml_content = re.sub(
            r'- name: Install SonarScanner[\s\S]*?run: dotnet tool install -g dotnet-sonarscanner[\s\S]*?(?=\n\s*- name:|\Z)', 
            '', yaml_content, flags=re.MULTILINE
        )

        # Remove "Begin SonarQube analysis" step
        yaml_content = re.sub(
            r'- name: Begin SonarQube analysis[\s\S]*?dotnet sonarscanner begin[\s\S]*?(?=\n\s*- name:|\Z)', 
            '', yaml_content, flags=re.MULTILINE
        )

        # Remove "End SonarQube analysis" step
        yaml_content = re.sub(
            r'- name: End SonarQube analysis[\s\S]*?dotnet sonarscanner end[^\n]*[\s\S]*?(?=\n\s*- name:|\Z)', 
            '', yaml_content, flags=re.MULTILINE
        )

        return yaml_content

    except Exception as e:
        logger.error(f"❌ Error while removing SonarScanner steps: {e}")
        return yaml_content
    
    

import re

def remove_dotnet_restore_step(yaml_content: str) -> str:
    """
    Removes GitHub Actions steps that run 'dotnet restore'.
    Handles variants like 'dotnet restore **/*.csproj'.
    """
    try:
        # This regex matches any step block that contains 'dotnet restore'
        pattern = re.compile(
            r'- name:.*?(?:\n\s{2,}.*?)*?run:.*?dotnet restore[^\n]*?(?:\n\s{2,}.*?)*?(?=\n\s*- name:|\Z)',
            re.MULTILINE | re.DOTALL
        )

        # Substitute matched block with empty string
        cleaned_yaml = pattern.sub('', yaml_content)

        return cleaned_yaml.strip()

    except Exception as e:
        print(f"❌ Error while removing dotnet restore step: {e}")
        return yaml_content




def remove_dotnet_build_step(yaml_content: str) -> str:
    """
    Removes GitHub Actions steps that run 'dotnet build'.
    Handles variants like 'dotnet build **/*.csproj'.
    """
    try:
        pattern = re.compile(
            r'- name:.*?(?:\n\s{2,}.*?)*?run:.*?dotnet build[^\n]*?(?:\n\s{2,}.*?)*?(?=\n\s*- name:|\Z)',
            re.MULTILINE | re.DOTALL
        )

        cleaned_yaml = pattern.sub('', yaml_content)

        return cleaned_yaml.strip()

    except Exception as e:
        print(f"❌ Error while removing dotnet build step: {e}")
        return yaml_content





def remove_dotnet_test_step(yaml_content: str) -> str:
    """
    Removes GitHub Actions steps that run 'dotnet test'.
    Handles variants like 'dotnet test **/*Tests/*.csproj'.
    """
    try:
        pattern = re.compile(
            r'- name:.*?(?:\n\s{2,}.*?)*?run:.*?dotnet test[^\n]*?(?:\n\s{2,}.*?)*?(?=\n\s*- name:|\Z)',
            re.MULTILINE | re.DOTALL
        )

        cleaned_yaml = pattern.sub('', yaml_content)
        return cleaned_yaml.strip()

    except Exception as e:
        print(f"❌ Error while removing dotnet test step: {e}")
        return yaml_content




def push_to_github(state: DevOpsState) -> DevOpsState:
    def get_config(attr: str, default: str = None) -> str:
        return getattr(state, attr, None) or os.getenv(attr.upper()) or default

    token = get_config("gh_token")
    if not token:
        raise ValueError("GitHub token not found in environment or state")

    repo_name = get_config("gh_repo", "your-org/your-repo")
    file_path = get_config("gh_file_path", ".github/workflows/generated_pipeline.yml")
    branch = get_config("gh_branch", "main")
    commit_msg = get_config("gh_commit_msg", "Add GitHub Actions workflow")

    raw_content = state.Devops_output or state.output
    if not raw_content:
        raise ValueError("No workflow content found in `Devops_output` or `output`")

    workflow_content = raw_content.strip()

    # Clean and fix the YAML content
    if "```" in workflow_content:
        workflow_content = extract_yaml_block(workflow_content)
    workflow_content = clean_yaml_fences(workflow_content)
    workflow_content = fix_setup_java_distribution(workflow_content)
    workflow_content = remove_java_gradle_steps(workflow_content)
    workflow_content = fix_sonar_scanner_commands(workflow_content)
    workflow_content = remove_sonar_scanner_steps(workflow_content)
    # workflow_content = remove_dotnet_restore_step(workflow_content)
    # workflow_content = remove_dotnet_build_step(workflow_content)
    # workflow_content = remove_dotnet_test_step(workflow_content)
    workflow_content = workflow_content.replace("/t:$SONAR_TOKEN", '/d:sonar.login="$SONAR_TOKEN"')
    workflow_content = workflow_content.replace("true:", "on:")
    workflow_content = workflow_content.encode("utf-8", "ignore").decode("utf-8")

    logger.info("🔍 Final cleaned YAML content:\n" + workflow_content)

    # Save file locally
    local_file_path = os.path.join(os.getcwd(), file_path)
    os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
    with open(local_file_path, 'w', encoding='utf-8') as f:
        f.write(workflow_content)
    logger.info(f"📁 Local file updated at {local_file_path}")

    # Push to GitHub
    try:
        github_client = Github(token)
        repo = github_client.get_repo(repo_name)

        try:
            contents = repo.get_contents(file_path, ref=branch)
            repo.update_file(
                path=contents.path,
                message=commit_msg,
                content=workflow_content,
                sha=contents.sha,
                branch=branch
            )
            logger.info(f"✅ GitHub Actions workflow updated in `{repo_name}` on branch `{branch}`")
        except UnknownObjectException:
            repo.create_file(
                path=file_path,
                message=commit_msg,
                content=workflow_content,
                branch=branch
            )
            logger.info(f"✅ GitHub Actions workflow created in `{repo_name}` on branch `{branch}`")

        state.github_status = "success"

    except GithubException as e:
        error_msg = f"❌ GitHub push failed: {getattr(e, 'data', {}).get('message', str(e))}"
        logger.error(error_msg)
        state.github_status = "failure"
        raise

    return state
