from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import textwrap

# Initialize FastAPI app
app = FastAPI()

# Allow CORS for all origins (you can restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI client (via OpenRouter)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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"
)

# Request body model
class QAItem(BaseModel):
    id: str
    question: str
    answer: str

class QARequest(BaseModel):
    qa_data: list[QAItem]

# Formatting function (same as your original)
def format_ai_response(text: str) -> str:
    lines = text.split("\n")
    formatted = []

    for line in lines:
        line = line.strip()
        if line.startswith(("1.", "2.", "3.", "-", "•")):
            formatted.append("  " + line)
        elif len(line) > 0 and len(line) < 50 and ":" not in line:
            formatted.append("\n" + line.upper() + "\n")
        else:
            formatted.append(textwrap.fill(line, width=80))
    return "\n".join(formatted)

# POST endpoint
@app.post("/analyze")
async def analyze_personality(request_data: QARequest):
    print("Data came from frontend")

    # Prepare prompt
    instructions = (
        "You act as a senior level professional development and training teacher. "
        "You analyze the following questions and answers based on your experience and determine:\n"
        "1. The personality of the person\n"
        "2. The careers that are suitable for them to choose\n"
        "3. Suggestions to improve their persona\n\n"
        "Please provide a comprehensive analysis in a well-structured format, concise enough to fit within two pages.\n\n"
        "Here are the answers:\n"
    )

    qa_text = "\n".join([f"{q.id}: {q.question} — {q.answer}" for q in request_data.qa_data])
    final_prompt = instructions + qa_text

    # Get LLM response
    completion = client.chat.completions.create(
        model="meta-llama/llama-3.3-70b-instruct:free",
        messages=[{"role": "user", "content": final_prompt}]
    )

    raw_response = completion.choices[0].message.content
    clean_response = format_ai_response(raw_response)

    # Return formatted response
    return {"analysis": clean_response}

# Run command:
# uvicorn main:app --reload
