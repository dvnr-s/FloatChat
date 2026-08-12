import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from mcp_use import MCPAgent, MCPClient

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv(os.path.join(BASE_DIR, ".env"))
YOUR_OPENAI_API_KEY = os.getenv("YOUR_OPENAI_API_KEY")
CONFIG_FILE = os.path.join(BASE_DIR, "S", "ocean.json")

# Global MCP client + agent. The agent is built on first request so the
# service still boots (and can report the problem) when the API key is missing.
client = MCPClient.from_config_file(CONFIG_FILE)
agent = None

def get_agent():
    global agent
    if agent is None:
        if not YOUR_OPENAI_API_KEY:
            raise RuntimeError(
                "YOUR_OPENAI_API_KEY is not set. Add it to the .env file in the "
                "project root and restart the server."
            )
        llm = ChatOpenAI(model="gpt-4o-mini", api_key=YOUR_OPENAI_API_KEY)
        agent = MCPAgent(llm=llm, client=client, max_steps=15, memory_enabled=True, verbose=False)
    return agent

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    if client and client.sessions:
        await client.close_all_sessions()

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Query(BaseModel):
    user_input: str

@app.get("/health")
async def health():
    return {"status": "ok", "openai_key_configured": bool(YOUR_OPENAI_API_KEY)}

@app.post("/chat")
async def chat(query: Query):
    try:
        response = await get_agent().run((query.user_input).split("Final Answer:")[-1].strip())
    except Exception as e:
        return {"response": f"⚠️ Agent error: {e}"}
    return {"response": response}