import time
import logging
import json
from openai import AsyncOpenAI
from app.core.config import settings
from app.repositories.mongodb.conversation_repository import conversation_repository
from app.repositories.mongodb.file_repository import file_repository

logger = logging.getLogger(__name__)

# In-memory storage for rate limits
# {user_id: last_request_time (float)}
_rate_limits = {}

# Initialize AsyncOpenAI client
if settings.openrouter_api_key:
    client = AsyncOpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1"
    )
else:
    client = None
    logger.warning("OPENROUTER_API_KEY is not set. AI agent features will not work.")

# Model configuration
MODEL = "dots-studio/dots-3-note-preview:free"
RATE_LIMIT_SECONDS = 2.0
MAX_HISTORY = 20

# System prompt
SYSTEM_PROMPT = """You are the AI assistant for Hunterstar File Transfer, a telegram bot for file management.
Your primary role is to help users manage their files, answer questions about the service, and assist them.
You have access to tools to look up the user's files. Use them when the user asks about their uploads.
Be helpful, natural, and friendly. While your focus is on file transfer, you can engage in normal conversation if it helps build rapport, but gently steer things back to your purpose if the conversation goes completely off-topic or becomes inappropriate."""

# Tool schemas
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_user_files",
            "description": "Get a list of the most recent files the user has uploaded to Hunterstar File Transfer.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_user_files",
            "description": "Search the user's files by name or category (e.g. document, photo, video, audio).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query (filename or category)."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_info",
            "description": "Get detailed information about a specific file by its share_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "share_id": {
                        "type": "string",
                        "description": "The unique share ID of the file."
                    }
                },
                "required": ["share_id"]
            }
        }
    }
]

async def execute_tool_call(user_id: int, tool_call) -> str:
    """Executes a tool call requested by the model and returns the result as a string."""
    name = tool_call.function.name
    try:
        arguments = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError:
        arguments = {}

    if name == "list_user_files":
        files = await file_repository.get_by_owner_id(user_id, limit=10)
        if not files:
            return "No files found for this user."
        result = []
        for f in files:
            result.append({
                "filename": f.original_filename,
                "size_mb": round(f.size / (1024 * 1024), 2),
                "type": getattr(f, "category", "document"),
                "share_id": f.share_id,
                "visibility": getattr(f.sharing, "mode", "private"),
                "created_at": f.created_at.isoformat() if hasattr(f, "created_at") else "unknown"
            })
        return json.dumps(result)

    elif name == "search_user_files":
        query = arguments.get("query", "").lower()
        files = await file_repository.get_by_owner_id(user_id, limit=50)
        matched = []
        for f in files:
            cat = getattr(f, "category", "").lower()
            fname = getattr(f, "original_filename", "").lower()
            if query in cat or query in fname:
                matched.append({
                    "filename": f.original_filename,
                    "size_mb": round(f.size / (1024 * 1024), 2),
                    "type": getattr(f, "category", "document"),
                    "share_id": f.share_id
                })
        if not matched:
            return f"No files matched the search query: {query}"
        return json.dumps(matched[:10])  # limit results to top 10

    elif name == "get_file_info":
        share_id = arguments.get("share_id")
        f = await file_repository.get_by_share_id(share_id)
        if not f or f.owner_id != user_id:
            return "File not found or access denied."
        info = {
            "filename": f.original_filename,
            "size_mb": round(f.size / (1024 * 1024), 2),
            "type": getattr(f, "category", "document"),
            "share_id": f.share_id,
            "visibility": getattr(f.sharing, "mode", "private"),
            "is_favorite": getattr(f, "is_favorite", False)
        }
        return json.dumps(info)

    else:
        return f"Unknown tool: {name}"

async def ask_agent(user_id: int, user_message: str) -> str:
    """
    Handles user interaction with the AI agent.
    Checks rate limits, appends to conversation history, and calls OpenRouter API.
    Handles tool calling loop if the model decides to use tools.
    """
    if not client:
        return "⚠️ The AI service is currently unconfigured (missing API key)."

    # Enforce rate limit (1 request per RATE_LIMIT_SECONDS)
    current_time = time.time()
    last_request_time = _rate_limits.get(user_id, 0)
    
    if current_time - last_request_time < RATE_LIMIT_SECONDS:
        return "⏳ Please wait a moment before sending another message."
        
    _rate_limits[user_id] = current_time

    # Record user message in DB
    user_msg_doc = {"role": "user", "content": user_message}
    await conversation_repository.add_message(user_id, user_msg_doc)

    # Fetch history
    history = await conversation_repository.get_history(user_id, limit=MAX_HISTORY)
    
    # Construct messages list with System prompt
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    # We will do a loop to handle multiple tool calls if necessary (max 5 iterations to avoid infinite loops)
    for _ in range(5):
        try:
            response = await client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                extra_body={"reasoning": {"enabled": True}}
            )
        except Exception as e:
            logger.error(f"Error calling OpenRouter API: {e}")
            return "⚠️ Sorry, I'm having trouble connecting to the AI service right now. Please try again later."

        response_message = response.choices[0].message
        
        # Build the message dict exactly as the SDK expects for further calls
        assistant_msg_doc = {"role": "assistant"}
        if response_message.content:
            assistant_msg_doc["content"] = response_message.content
            
        tool_calls = response_message.tool_calls
        if tool_calls:
            # Add tool calls to the history to maintain conversation state
            assistant_msg_doc["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                } for tc in tool_calls
            ]
            
            # Save assistant message with tool_calls to DB
            await conversation_repository.add_message(user_id, assistant_msg_doc)
            messages.append(assistant_msg_doc)

            # Execute all tool calls
            for tool_call in tool_calls:
                tool_result_content = await execute_tool_call(user_id, tool_call)
                tool_msg_doc = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": tool_result_content
                }
                await conversation_repository.add_message(user_id, tool_msg_doc)
                messages.append(tool_msg_doc)
                
            # Loop continues, sending the tool results back to the model
            continue
            
        else:
            # Normal text response
            if response_message.content:
                # Save assistant text message to DB
                await conversation_repository.add_message(user_id, {"role": "assistant", "content": response_message.content})
                return response_message.content
            else:
                return "⚠️ Received an empty response from the AI."
                
    return "⚠️ The AI agent got stuck in a loop and couldn't complete the request."

