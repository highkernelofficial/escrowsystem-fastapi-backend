import os
import json
from dotenv import load_dotenv
from typing import Dict

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.messages import SystemMessage, HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import ToolMessage

from app.schemas.ai_schema import (
    GenerateRequest,
    EvaluateRequest,
    GenerateMilestoneResponse,
    EvaluateResponse,
)

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GITHUB_PAT = os.getenv("GITHUB_PAT")

# -----------------------------
# MODEL
# -----------------------------
model = ChatGoogleGenerativeAI(
    model="gemini-3-flash-preview",
    google_api_key=GOOGLE_API_KEY,
    temperature=0.3
)

# ----------------------------------
# GENERATE MILESTONES
# ----------------------------------
def generate_milestones(req: GenerateRequest) -> Dict:

    messages = [
        SystemMessage(
            content="""
You are an expert project manager.

Break the project into milestones and distribute budget.

Rules:
- 3 to 5 milestones
- Each must include: title, description, percentage, amount
- Total percentage MUST equal 100
- Core development should have highest allocation
- Return ONLY valid JSON
"""
        ),
        HumanMessage(
            content=f"""
Project:
Title: {req.title}
Description: {req.description}
Tech Stack: {req.tech_stack}
Expected Outcome: {req.expected_outcome}
Total Budget: {req.total_budget}

Return JSON:
{{
  "milestones": [
    {{
      "title": "...",
      "description": "...",
      "percentage": number,
      "amount": number
    }}
  ]
}}
"""
        )
    ]

    structured_model = model.with_structured_output(GenerateMilestoneResponse)

    try:
        response = structured_model.invoke(messages)
        data = response.model_dump()
        return normalize_budget(data, req.total_budget)
    except Exception:
        return fallback_milestones(req.total_budget)


# ----------------------------------
# MCP TOOL LOADER
# ----------------------------------
async def create_mcp_tools():
    client = MultiServerMCPClient(
        {
            "github": {
                "transport": "http",
                "url": "https://api.githubcopilot.com/mcp/",
                "headers": {
                    "Authorization": f"Bearer {GITHUB_PAT}"
                },
            }
        }
    )

    tools = await client.get_tools()

    print(f"Loaded {len(tools)} MCP tools:")
    for t in tools:
        print(f"  - {t.name}")

    return tools


# ----------------------------------
# SAFE CONTENT EXTRACTOR
# ----------------------------------
def extract_text_content(response):
    if isinstance(response.content, str):
        return response.content.strip()

    elif isinstance(response.content, list):
        text_parts = []
        for part in response.content:
            if isinstance(part, dict) and part.get("type") == "text":
                text_parts.append(part.get("text", ""))
        return " ".join(text_parts).strip()

    return str(response.content)


# ----------------------------------
# EXTRACT REPO INFO
# ----------------------------------
def extract_repo_info(url: str):
    import re
    match = re.search(r"github\.com/([^/]+)/([^/]+)", url)
    if match:
        return match.group(1), match.group(2)
    return None, None


# ----------------------------------
# EVALUATE SUBMISSION (FINAL 🔥)
# ----------------------------------
async def evaluate_submission(req: EvaluateRequest):

    tools = await create_mcp_tools()
    named_tools = {tool.name: tool for tool in tools}

    llm_with_tools = model.bind_tools(tools)

    owner, repo = extract_repo_info(req.submission)

    prompt = f"""
You are a helpful AI.

Repository:
Owner: {owner}
Repo: {repo}

Task:
- Use tools to explore this repository
- Read README
- Check files
- Explain what this project does
- Check if FastAPI is used

IMPORTANT:
- DO NOT ask user anything
- DO NOT return JSON
- Just explain clearly
"""

    messages = [{"role": "user", "content": prompt}]

    # -----------------------------
    # TOOL LOOP
    # -----------------------------
    for _ in range(6):

        response = await llm_with_tools.ainvoke(messages)

        print("RAW RESPONSE:", response)

        # ✅ FINAL TEXT RESPONSE
        if not getattr(response, "tool_calls", None):

            content = extract_text_content(response)

            # 🔥 force retry if empty
            if not content:
                messages.append({
                    "role": "user",
                    "content": "Now give the final explanation of the repository."
                })
                continue

            # -----------------------------
            # 🔥 STEP 2: STRUCTURED EVALUATION
            # -----------------------------
            eval_prompt = f"""
Based on this repository analysis:

{content}

Evaluate:

- Score (0-100)
- Approve if meaningful implementation exists
- Keep feedback short

Return ONLY JSON:
{{
  "score": number,
  "approved": true/false,
  "feedback": "short explanation"
}}
"""

            eval_response = await model.ainvoke(eval_prompt)
            eval_text = extract_text_content(eval_response)

            try:
                start = eval_text.find("{")
                end = eval_text.rfind("}") + 1
                parsed = json.loads(eval_text[start:end])

                return EvaluateResponse(**parsed).model_dump()

            except Exception:
                return {
                    "score": 50,
                    "approved": False,
                    "feedback": "Evaluation parsing failed"
                }

        # -----------------------------
        # TOOL EXECUTION
        # -----------------------------
        tool_messages = []

        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc.get("args", {})
            tool_id = tc["id"]

            print(f"Calling tool: {tool_name}")

            try:
                result = await named_tools[tool_name].ainvoke(tool_args)
            except Exception as e:
                result = {"error": str(e)}

            tool_messages.append(
                ToolMessage(
                    tool_call_id=tool_id,
                    content=json.dumps(result)
                )
            )

        messages.extend([response, *tool_messages])

    return {
        "score": 50,
        "approved": False,
        "feedback": "Evaluation incomplete"
    }


# ----------------------------------
# NORMALIZE BUDGET
# ----------------------------------
def normalize_budget(data, total_budget):
    milestones = data.get("milestones", [])

    total = sum(m.get("amount", 0) for m in milestones)

    if total == 0:
        return fallback_milestones(total_budget)

    scale = total_budget / total

    for m in milestones:
        m["amount"] = round(m["amount"] * scale, 2)

    return {"milestones": milestones}


# ----------------------------------
# FALLBACK
# ----------------------------------
def fallback_milestones(total_budget):
    return {
        "milestones": [
            {
                "title": "Setup",
                "description": "Project initialization",
                "percentage": 20,
                "amount": round(total_budget * 0.2, 2)
            },
            {
                "title": "Development",
                "description": "Core implementation",
                "percentage": 60,
                "amount": round(total_budget * 0.6, 2)
            },
            {
                "title": "Testing",
                "description": "Testing & deployment",
                "percentage": 20,
                "amount": round(total_budget * 0.2, 2)
            }
        ]
    }