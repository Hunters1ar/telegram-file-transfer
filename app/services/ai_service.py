import time
import logging
import json
import re
from openai import AsyncOpenAI
from app.core.config import settings
from app.repositories.mongodb.conversation_repository import conversation_repository
from app.repositories.mongodb.file_repository import file_repository
from app.repositories.mongodb.folder_repository import folder_repository
from app.domain.entities.folder import FolderMetadata
from bson import ObjectId
from datetime import datetime, timezone

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

# Validation helper
def validate_name(name: str) -> str:
    """Validates and sanitizes a folder or file name."""
    if not name:
        raise ValueError("Name cannot be empty.")
    
    # Strip whitespace
    name = name.strip()
    
    # Check max length
    if len(name) > 255:
        raise ValueError("Name cannot exceed 255 characters.")
        
    # Reject path separators
    if '/' in name or '\\' in name:
        raise ValueError("Name cannot contain '/' or '\\'.")
        
    # Windows reserved names
    reserved_names = {
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
    }
    base_name = name.split('.')[0].upper()
    if base_name in reserved_names:
        raise ValueError("This name is reserved and cannot be used.")
        
    return name

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
    },
    {
        "type": "function",
        "function": {
            "name": "rename_file",
            "description": "Rename a specific file by its share_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "share_id": {
                        "type": "string",
                        "description": "The unique share ID of the file."
                    },
                    "new_name": {
                        "type": "string",
                        "description": "The new name for the file. Note: The tool automatically preserves the original extension unless you explicitly provide a different one."
                    }
                },
                "required": ["share_id", "new_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_folder",
            "description": "Create a new folder for the user (or returns the existing folder ID if it already exists).",
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_name": {
                        "type": "string",
                        "description": "The name of the folder to create."
                    }
                },
                "required": ["folder_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_folders",
            "description": "List all folders owned by the user.",
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
            "name": "move_file",
            "description": "Move a specific file into a folder by their IDs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "share_id": {
                        "type": "string",
                        "description": "The unique share ID of the file."
                    },
                    "folder_id": {
                        "type": "string",
                        "description": "The unique ID of the folder to move the file into. (Get this from list_folders or create_folder)"
                    }
                },
                "required": ["share_id", "folder_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_storage_stats",
            "description": "Get statistics about the user's storage usage, including total size, downloads, and a breakdown of files by category.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
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
        files = await file_repository.get_by_owner_id(user_id, limit=20)
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
                "folder_id": f.folder_id,
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
                    "share_id": f.share_id,
                    "folder_id": f.folder_id
                })
        if not matched:
            return f"No files matched the search query: {query}"
        return json.dumps(matched[:20])

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
            "is_favorite": getattr(f, "is_favorite", False),
            "folder_id": f.folder_id
        }
        return json.dumps(info)

    elif name == "rename_file":
        share_id = arguments.get("share_id")
        new_name = arguments.get("new_name")
        
        f = await file_repository.get_by_share_id(share_id)
        if not f or f.owner_id != user_id:
            return "File not found or access denied."
            
        try:
            clean_name = validate_name(new_name)
        except ValueError as e:
            return f"Error: {str(e)}"
            
        # Preserve extension if not provided in the new name
        original_ext = f.extension
        if original_ext and not clean_name.endswith(f".{original_ext}") and "." not in clean_name:
            clean_name = f"{clean_name}.{original_ext}"
            
        f.original_filename = clean_name
        await file_repository.update(f)
        return f"Success. File renamed to '{clean_name}'"

    elif name == "create_folder":
        folder_name = arguments.get("folder_name")
        try:
            clean_name = validate_name(folder_name)
        except ValueError as e:
            return f"Error: {str(e)}"
            
        # Check if already exists
        folders = await folder_repository.get_by_owner_id(user_id, limit=100)
        for folder in folders:
            if folder.name.lower() == clean_name.lower():
                return f"Folder already exists. folder_id: {folder.id}"
                
        # Create new folder
        new_folder = FolderMetadata(
            _id=str(ObjectId()),
            name=clean_name,
            owner_id=user_id,
            created_at=datetime.now(timezone.utc)
        )
        await folder_repository.save(new_folder)
        return f"Success. Folder created. folder_id: {new_folder.id}"

    elif name == "list_folders":
        folders = await folder_repository.get_by_owner_id(user_id, limit=50)
        if not folders:
            return "No folders found."
        
        result = [{"id": folder.id, "name": folder.name} for folder in folders]
        return json.dumps(result)

    elif name == "move_file":
        share_id = arguments.get("share_id")
        folder_id = arguments.get("folder_id")
        
        f = await file_repository.get_by_share_id(share_id)
        if not f or f.owner_id != user_id:
            return "File not found or access denied."
            
        # Validate folder
        folder = await folder_repository.get_by_id(folder_id)
        if not folder or folder.owner_id != user_id:
            return "Folder not found or access denied."
            
        f.folder_id = folder_id
        await file_repository.update(f)
        return "Success. File moved."

    elif name == "get_storage_stats":
        stats = await file_repository.get_user_stats(user_id)
        return json.dumps(stats)

    else:
        return f"Unknown tool: {name}"

async def ask_agent(user_id: int, user_message: str, lang: str = "en") -> str:
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
    dynamic_system_prompt = SYSTEM_PROMPT + f"\nIMPORTANT: Always communicate with the user in their preferred language/locale code '{lang}', or whichever language they speak in. Do not default to English unless requested."
    messages = [{"role": "system", "content": dynamic_system_prompt}] + history

    # We will do a loop to handle multiple tool calls if necessary (max 15 iterations to avoid infinite loops)
    for _ in range(15):
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
                
    return "⚠️ The AI agent exceeded its maximum operation limit. Please try splitting your request into smaller parts."

