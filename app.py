import os
import gradio as gr
import requests
import pandas as pd
from dotenv import load_dotenv

from openai import OpenAI
from langchain_openai import ChatOpenAI
import logging
from tools import (
    multiply,
    add,
    subtract,
    divide,
    modulus,
    wiki_search,
    web_search,
    arvix_search,
    youtube_transcript,
    file_tool,
)
from agent import Agent
import mimetypes
import tempfile
from typing import Any, Dict, List


load_dotenv()

# --- Constants ---
DEFAULT_API_URL = "localhost" #os.getenv("DEFAULT_API_URL", "https://agents-course-unit4-scoring.hf.space")
client = OpenAI()
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

# --- run_and_submit_all unchanged except instantiating Agent above ---


def run_and_submit_all(profile: gr.OAuthProfile | None):
    space_id = os.getenv("SPACE_ID")
    space_host = os.getenv("SPACE_HOST")
    if profile:
        username = profile.username
    else:
        return "Please Login to Hugging Face with the button.", None

    api_url = DEFAULT_API_URL
    questions_url = f"{api_url}/questions"
    submit_url = f"{api_url}/submit"
    files_url = f"{api_url}/files"

    # Instantiate Agent and Tools
    try:
        with open("system_prompt.txt", "r") as f:
            prompt = f.read()
    except Exception:
        prompt = ""

    tools = [
        multiply,
        add,
        subtract,
        divide,
        modulus,
        wiki_search,
        web_search,
        arvix_search,
        youtube_transcript,
        file_tool,
    ]
    model = ChatOpenAI(model="o3-2025-04-16")
    agent = Agent(model, tools, system=prompt)

    agent_code = f"https://huggingface.co/spaces/{space_host}/{space_id}/tree/main"
    # Fetch questions
    questions_data: List[Dict[str, Any]] = []
    try:
        response = requests.get(questions_url, timeout=15)
        response.raise_for_status()
        questions_data_raw = response.json()
        if not isinstance(questions_data_raw, list):
            return "Error: questions endpoint did not return a list.", None
        questions_data = [q for q in questions_data_raw if isinstance(q, dict)]
    except Exception as e:
        return f"Error fetching questions: {e}", None

    results_log = []
    answers_payload = []

    # Prepare download directory once
    temp_base = tempfile.gettempdir()
    download_dir = os.path.join(temp_base, "agent_files")
    os.makedirs(download_dir, exist_ok=True)

    for item in questions_data or []:
        task_id = item.get("task_id")
        question_text = item.get("question")
        if not task_id or question_text is None:
            continue

        # 1. Download associated file, if available
        local_path = None
        file_url = f"{files_url}/{task_id}"
        try:
            resp = requests.get(file_url, timeout=15)
            if resp.status_code == 200 and resp.content:
                # Determine extension:
                parsed_ext = None
                path_lower = file_url.lower()
                for ext in [
                    ".xlsx",
                    ".xls",
                    ".py",
                    ".mp3",
                    ".wav",
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".csv",
                    ".txt",
                ]:
                    if path_lower.endswith(ext):
                        parsed_ext = ext
                        break
                if not parsed_ext:
                    ct = resp.headers.get("Content-Type", "")
                    ext_guess = mimetypes.guess_extension(ct.split(";")[0].strip())
                    if ext_guess:
                        parsed_ext = ext_guess
                if not parsed_ext:
                    parsed_ext = ""
                filename = f"{task_id}{parsed_ext}"
                local_path = os.path.join(download_dir, filename)
                with open(local_path, "wb") as f:
                    f.write(resp.content)
                logger.info(f"Downloaded file for task {task_id} to {local_path}")
            else:
                logger.info(
                    f"No file or empty content for task {task_id} (status {resp.status_code})"
                )
        except Exception as e:
            logger.warning(
                f"Failed to download file for task {task_id} from {file_url}: {e}"
            )
            local_path = None

        # 2. Call the agent, passing the local_path so it knows a file is available
        try:
            ans = agent(question_text, local_path)
            answers_payload.append({"task_id": task_id, "submitted_answer": ans})
            results_log.append(
                {
                    "Task ID": task_id,
                    "Question": question_text,
                    "File Path": local_path or "",
                    "Submitted Answer": ans,
                }
            )
        except Exception as e:
            logger.error(f"Agent error on task {task_id}: {e}", exc_info=True)
            results_log.append(
                {
                    "Task ID": task_id,
                    "Question": question_text,
                    "File Path": local_path or "",
                    "Submitted Answer": f"AGENT ERROR: {e}",
                }
            )

    if not answers_payload:
        return "Agent did not produce any answers to submit.", pd.DataFrame(results_log)

    submission_data = {
        "username": username.strip(),
        "agent_code": agent_code,
        "answers": answers_payload,
    }
    # Submission as before...
    try:
        resp2 = requests.post(submit_url, json=submission_data, timeout=60)
        resp2.raise_for_status()
        data = resp2.json()
        final_status = (
            f"Submission Successful!\n"
            f"User: {data.get('username')}\n"
            f"Overall Score: {data.get('score', 'N/A')}% "
            f"({data.get('correct_count', '?')}/{data.get('total_attempted', '?')} correct)\n"
            f"Message: {data.get('message', 'No message received.')}"
        )
        return final_status, pd.DataFrame(results_log)
    except requests.exceptions.HTTPError as e:
        detail = f"Server responded with status {e.response.status_code}."
        try:
            jd = e.response.json()
            detail += f" Detail: {jd.get('detail', e.response.text)}"
        except Exception:
            detail += f" Response: {e.response.text[:500]}"
        return f"Submission Failed: {detail}", pd.DataFrame(results_log)
    except Exception as e:
        return f"Submission Failed: {e}", pd.DataFrame(results_log)


# --- Gradio Interface (unchanged) ---
with gr.Blocks() as demo:
    gr.Markdown("# Basic Agent Evaluation Runner")
    gr.Markdown(
        """
        **Instructions:**
        1. Clone and modify the code to define your agent's logic/tools.
        2. Log in to Hugging Face.
        3. Click 'Run Evaluation & Submit All Answers'.
        """
    )
    gr.LoginButton()
    run_button = gr.Button("Run Evaluation & Submit All Answers")
    status_output = gr.Textbox(
        label="Run Status / Submission Result", lines=5, interactive=False
    )
    results_table = gr.DataFrame(label="Questions and Agent Answers", wrap=True)
    run_button.click(fn=run_and_submit_all, outputs=[status_output, results_table])

if __name__ == "__main__":
    space_host = os.getenv("SPACE_HOST")
    space_id = os.getenv("SPACE_ID")
    if space_host:
        print(f"✅ SPACE_HOST found: {space_host}")
    else:
        print("ℹ️ SPACE_HOST not found.")
    if space_id:
        print(f"✅ SPACE_ID found: {space_id}")
    else:
        print("ℹ️ SPACE_ID not found.")
    
    # Configure for Docker/deployment
    server_name = os.getenv("GRADIO_SERVER_NAME", "0.0.0.0")
    server_port = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
    share_gradio = os.getenv("GRADIO_SHARE", "false").lower() == "true"
    
    print("Launching Gradio Interface...")
    demo.launch(
        server_name=server_name,
        server_port=server_port,
        share=share_gradio,
        debug=True
    )
