from typing_extensions import TypedDict, NotRequired
from langgraph.graph import StateGraph, START, END
from PIL import Image as PILImage
from dotenv import load_dotenv
import io
import os
import time
import requests
import base64
from typing import Optional

from langchain_google_vertexai import ChatVertexAI

# Load environment variables
load_dotenv(dotenv_path=".dev.env")

# Initialize LLM
llm = ChatVertexAI(
    model="gemini-2.5-pro",
    temperature=0,
    max_tokens=2000,
    max_retries=6,
    stop=None,
)

# Environment variables for APIs
SLACK_TOKEN = os.getenv("SLACK_TOKEN")
SLACK_API_BASE = "https://slack.com/api"
AZURE_DEVOPS_PAT = os.getenv("AZURE_DEVOPS_TOKEN")  # Personal Access Token
AZURE_DEVOPS_ORG = os.getenv("AZURE_DEVOPS_ORG")
AZURE_DEVOPS_PROJECT = os.getenv("AZURE_DEVOPS_PROJECT")
AZURE_DEVOPS_PIPELINE_ID = os.getenv("AZURE_DEVOPS_PIPELINE_ID")

# Azure DevOps requires Base64 encoded token (format: :token)
AZURE_DEVOPS_TOKEN = base64.b64encode(f":{AZURE_DEVOPS_PAT}".encode()).decode() if AZURE_DEVOPS_PAT else None

# Graph state
class State(TypedDict):
    channel: str  # Slack channel name or ID
    slack_messages: NotRequired[list]  # Messages from Slack
    albert_message: NotRequired[str]  # Message from Albert H. found
    llm_approval: NotRequired[str]  # LLM evaluation result ("Approved" or "Rejected")
    pipeline_id: NotRequired[int]  # Azure DevOps pipeline ID
    build_id: NotRequired[int]  # Azure DevOps build ID
    build_status: NotRequired[str]  # Build status (e.g., "Completed", "InProgress")
    error: NotRequired[str]  # Error message if any


# Helper functions for Slack API
def get_slack_channel_id(channel_name: str) -> Optional[str]:
    """Get Slack channel ID from channel name"""
    headers = {
        "Authorization": f"Bearer {SLACK_TOKEN}",
        "Content-Type": "application/json"
    }
    response = requests.get(
        f"{SLACK_API_BASE}/conversations.list",
        headers=headers,
        params={"types": "public_channel,private_channel"}
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get("ok"):
            for channel in data.get("channels", []):
                if channel.get("name") == channel_name or channel.get("id") == channel_name:
                    return channel.get("id")
    return None


def get_slack_messages(channel_id: str, limit: int = 100) -> list:
    """Get messages from Slack channel"""
    headers = {
        "Authorization": f"Bearer {SLACK_TOKEN}",
        "Content-Type": "application/json"
    }
    response = requests.get(
        f"{SLACK_API_BASE}/conversations.history",
        headers=headers,
        params={"channel": channel_id, "limit": limit}
    )
    
    if response.status_code == 200:
        data = response.json()
        if data.get("ok"):
            return data.get("messages", [])
    return []


# Helper functions for Azure DevOps API
def trigger_azure_pipeline(pipeline_id: int, branch: str = "main") -> Optional[dict]:
    """Trigger Azure DevOps pipeline"""
    if not AZURE_DEVOPS_TOKEN:
        return None
    
    headers = {
        "Authorization": f"Basic {AZURE_DEVOPS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    url = (
        f"https://dev.azure.com/{AZURE_DEVOPS_ORG}/{AZURE_DEVOPS_PROJECT}/"
        f"_apis/pipelines/{pipeline_id}/runs?api-version=7.1"
    )
    
    payload = {
        "resources": {
            "repositories": {
                "self": {
                    "refName": f"refs/heads/{branch}"
                }
            }
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error triggering pipeline: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Exception triggering pipeline: {str(e)}")
        return None


def get_pipeline_status(pipeline_id: int, run_id: int) -> Optional[dict]:
    """Get Azure DevOps pipeline run status"""
    if not AZURE_DEVOPS_TOKEN:
        return None
    
    headers = {
        "Authorization": f"Basic {AZURE_DEVOPS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    url = (
        f"https://dev.azure.com/{AZURE_DEVOPS_ORG}/{AZURE_DEVOPS_PROJECT}/"
        f"_apis/pipelines/{pipeline_id}/runs/{run_id}?api-version=7.1"
    )
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting pipeline status: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Exception getting pipeline status: {str(e)}")
        return None


# Nodes
def consult_slack_messages(state: State):
    """Node 1: Consult Slack messages from a specific channel"""
    channel = state["channel"]
    
    try:
        # Get channel ID
        channel_id = get_slack_channel_id(channel)
        if not channel_id:
            return {
                "error": f"Channel '{channel}' not found or not accessible"
            }
        
        # Get messages
        messages = get_slack_messages(channel_id)
        
        return {
            "slack_messages": messages
        }
    except Exception as e:
        return {
            "error": f"Error fetching Slack messages: {str(e)}"
        }


def check_albert_message(state: State):
    """Node 1a: Check for Albert H. message and evaluate with LLM"""
    messages = state.get("slack_messages", [])
    albert_message = None
    
    # Find message from Albert H.
    for message in messages:
        user_id = message.get("user", "")
        # Get user info to check name
        try:
            headers = {
                "Authorization": f"Bearer {SLACK_TOKEN}",
                "Content-Type": "application/json"
            }
            user_response = requests.get(
                f"{SLACK_API_BASE}/users.info",
                headers=headers,
                params={"user": user_id}
            )
            if user_response.status_code == 200:
                user_data = user_response.json()
                if user_data.get("ok"):
                    user_name = user_data.get("user", {}).get("real_name", "")
                    display_name = user_data.get("user", {}).get("profile", {}).get("display_name", "")
                    # Check if user is Albert H.
                    if "Albert H." in user_name or "Albert H." in display_name:
                        albert_message = message.get("text", "")
                        break
        except:
            # If we can't check user name, check if user field contains albert
            # This is a fallback - in production you'd want to store user mapping
            pass
    
    if not albert_message:
        return {
            "albert_message": "",
            "llm_approval": "Rejected",
            "error": "No message from Albert H. found in channel"
        }
    
    # Evaluate with LLM
    try:
        prompt = (
            f"Review the following Slack message from Albert H.:\n\n"
            f"{albert_message}\n\n"
            f"Determine if we should proceed with triggering the Azure DevOps pipeline. "
            f"Respond with 'Approved' if we should proceed, or 'Rejected' if we should not. "
            f"Only respond with one word: 'Approved' or 'Rejected'."
        )
        
        msg = llm.invoke(prompt)
        approval = msg.content.strip()
        
        # Ensure it's either Approved or Rejected
        if "Approved" in approval:
            approval = "Approved"
        else:
            approval = "Rejected"
        
        return {
            "albert_message": albert_message,
            "llm_approval": approval
        }
    except Exception as e:
        return {
            "albert_message": albert_message,
            "llm_approval": "Rejected",
            "error": f"Error evaluating message with LLM: {str(e)}"
        }


def validate_approval(state: State):
    """Gate function: Validate LLM approval"""
    approval = state.get("llm_approval", "")
    if approval == "Approved":
        return "Approved"
    return "Rejected"


def trigger_pipeline(state: State):
    """Node 2: Trigger Azure DevOps pipeline"""
    try:
        if not AZURE_DEVOPS_PIPELINE_ID:
            return {
                "error": "Azure DevOps pipeline ID not configured"
            }
        
        pipeline_id = int(AZURE_DEVOPS_PIPELINE_ID)
        result = trigger_azure_pipeline(pipeline_id)
        
        if result:
            # Extract build/run ID from response
            build_id = result.get("id")
            if not build_id:
                # Try to extract from _links
                href = result.get("_links", {}).get("self", {}).get("href", "")
                if href:
                    # Extract ID from URL like: .../runs/{id}
                    parts = href.split("/")
                    for i, part in enumerate(parts):
                        if part == "runs" and i + 1 < len(parts):
                            build_id = parts[i + 1]
                            break
            
            if build_id:
                return {
                    "pipeline_id": pipeline_id,
                    "build_id": int(build_id) if isinstance(build_id, (str, int)) else pipeline_id,
                    "build_status": "InProgress"
                }
            else:
                return {
                    "error": "Failed to extract build ID from pipeline trigger response",
                    "pipeline_id": pipeline_id
                }
        else:
            return {
                "error": "Failed to trigger Azure DevOps pipeline - check logs for details"
            }
    except ValueError as e:
        return {
            "error": f"Invalid pipeline ID format: {str(e)}"
        }
    except Exception as e:
        return {
            "error": f"Error triggering pipeline: {str(e)}"
        }


def check_pipeline_status(state: State):
    """Node 2a: Check pipeline status with polling"""
    pipeline_id = state.get("pipeline_id")
    build_id = state.get("build_id")  # This is the run_id from pipeline trigger
    
    if not pipeline_id or not build_id:
        return {
            "error": "No pipeline ID or build ID available"
        }
    
    # Wait 3 seconds before first check
    print("Waiting 3 seconds before first status check...")
    time.sleep(3)
    
    max_attempts = 100  # Maximum polling attempts (5 minutes with 3s intervals)
    attempt = 0
    
    print(f"Starting status polling for pipeline {pipeline_id}, run {build_id}...")
    
    while attempt < max_attempts:
        try:
            run_info = get_pipeline_status(pipeline_id, build_id)
            
            if run_info:
                state_value = run_info.get("state", "").lower()
                result_value = run_info.get("result", "").lower() if run_info.get("result") else None
                
                # Check if completed
                if state_value == "completed":
                    if result_value:
                        status_msg = f"Completed - {result_value.capitalize()}"
                    else:
                        status_msg = "Completed"
                    print(f"Pipeline run {build_id} completed with status: {status_msg}")
                    return {
                        "build_status": status_msg
                    }
                else:
                    # Still in progress, log and wait
                    current_status = run_info.get("state", "Unknown")
                    print(f"Pipeline run {build_id} status: {current_status} (attempt {attempt + 1}/{max_attempts})")
                    time.sleep(3)
                    attempt += 1
            else:
                # If we can't get status, wait and retry
                print(f"Unable to get status for run {build_id}, retrying... (attempt {attempt + 1}/{max_attempts})")
                time.sleep(3)
                attempt += 1
                
        except Exception as e:
            return {
                "error": f"Error checking pipeline status: {str(e)}"
            }
    
    # If we exhausted attempts
    print(f"Pipeline status check timed out after {max_attempts} attempts")
    return {
        "build_status": "Timeout - Status check exceeded maximum attempts",
        "error": "Pipeline status check timed out"
    }


# Build workflow
workflow = StateGraph(State)

# Add nodes
workflow.add_node("consult_slack_messages", consult_slack_messages)
workflow.add_node("check_albert_message", check_albert_message)
workflow.add_node("trigger_pipeline", trigger_pipeline)
workflow.add_node("check_pipeline_status", check_pipeline_status)

# Add edges
workflow.add_edge(START, "consult_slack_messages")
workflow.add_edge("consult_slack_messages", "check_albert_message")
workflow.add_conditional_edges(
    "check_albert_message",
    validate_approval,
    {
        "Approved": "trigger_pipeline",
        "Rejected": END
    }
)
workflow.add_edge("trigger_pipeline", "check_pipeline_status")
workflow.add_edge("check_pipeline_status", END)

# Compile
chain = workflow.compile()

# Example invocation
if __name__ == "__main__":
    # Show workflow graph BEFORE execution
    print("=" * 60)
    print("Generating workflow graph...")
    print("=" * 60)
    
    graph_image = chain.get_graph().draw_mermaid_png()
    
    # Save the graph image to file
    graph_file = "workflow_graph_v2.png"
    with open(graph_file, "wb") as f:
        f.write(graph_image)
    print(f"✓ Workflow graph saved to: {graph_file}")
    
    # Display the graph image
    img = PILImage.open(io.BytesIO(graph_image))
    img.show()  # Abrirá la imagen con el visor predeterminado
    print("✓ Workflow graph displayed")
    print("=" * 60)
    print("\nStarting workflow execution...\n")
    
    # Example usage - replace with actual channel name
    state = chain.invoke({"channel": "general"})
    
    print("\n=== Workflow Execution Result ===\n")
    print(f"Channel: {state.get('channel')}")
    print(f"Messages found: {len(state.get('slack_messages', []))}")
    print(f"Albert H. message: {state.get('albert_message', 'Not found')}")
    print(f"LLM Approval: {state.get('llm_approval', 'N/A')}")
    print(f"Pipeline ID: {state.get('pipeline_id', 'N/A')}")
    print(f"Build ID: {state.get('build_id', 'N/A')}")
    print(f"Build Status: {state.get('build_status', 'N/A')}")
    
    if state.get('error'):
        print(f"Error: {state.get('error')}")

