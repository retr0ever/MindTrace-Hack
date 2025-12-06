"""
Gemini Provider implementation for the unified LLM interface.
"""

import asyncio
import json
import os
import time
import uuid
from typing import List, Dict, Any, Optional, AsyncIterator
from logging import getLogger
from uuid import uuid4

from google import genai
from google.genai import types

from spoon_ai.schema import Message, ToolCall, Function, LLMResponseChunk
from spoon_ai.callbacks.manager import CallbackManager
from ..interface import LLMProviderInterface, LLMResponse, ProviderMetadata, ProviderCapability
from ..errors import ProviderError, AuthenticationError, RateLimitError, ModelNotFoundError, NetworkError
from ..registry import register_provider

logger = getLogger(__name__)


@register_provider("gemini", [
    ProviderCapability.CHAT,
    ProviderCapability.COMPLETION,
    ProviderCapability.STREAMING,
    ProviderCapability.TOOLS,
    ProviderCapability.IMAGE_GENERATION,
    ProviderCapability.VISION
])
class GeminiProvider(LLMProviderInterface):
    """Gemini provider implementation."""
    
    def __init__(self):
        self.client: Optional[genai.Client] = None
        self.config: Dict[str, Any] = {}
        self.model: str = ""
        self.max_tokens: int = 4096
        self.temperature: float = 0.3
        
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the Gemini provider with configuration."""
        try:
            self.config = config
            self.model = config.get('model', 'gemini-2.5-pro')
            self.max_tokens = config.get('max_tokens', 4096)
            self.temperature = config.get('temperature', 0.3)
            
            api_key = config.get('api_key')
            if not api_key:
                raise AuthenticationError("gemini", context={"config": config})
            
            self.client = genai.Client(api_key=api_key)
            
            logger.info(f"Gemini provider initialized with model: {self.model}")
            
        except Exception as e:
            if isinstance(e, (AuthenticationError, ProviderError)):
                raise
            raise ProviderError("gemini", f"Failed to initialize: {str(e)}", original_error=e)
    
    def _convert_messages(self, messages: List[Message]) -> tuple[Optional[str], str]:
        """Convert Message objects to Gemini format for simple chat."""
        system_content = ""
        user_message = ""
        
        # Extract system messages
        for message in messages:
            if message.role == "system":
                if system_content:
                    system_content += " " + message.content
                else:
                    system_content = message.content
        
        # Get the last user message
        for message in reversed(messages):
            if message.role == "user":
                user_message = message.content
                break
        
        # If no user message found, use a default
        if not user_message:
            user_message = "Hello"
        
        return system_content, user_message
    
    def _convert_messages_for_tools(self, messages: List[Message]) -> tuple[Optional[str], List]:
        """Convert Message objects to Gemini format for tool calling."""
        system_content = ""
        gemini_messages = []
        
        for message in messages:
            if message.role == "system":
                if system_content:
                    system_content += " " + message.content
                else:
                    system_content = message.content
            elif message.role == "user":
                gemini_messages.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=message.content)]
                ))
            elif message.role == "assistant":
                if message.tool_calls:
                    # Convert tool calls to Gemini format
                    parts = []
                    if message.content:
                        parts.append(types.Part.from_text(text=message.content))
                    
                    for tool_call in message.tool_calls:
                        args = tool_call.function.get_arguments_dict()
                        parts.append(types.Part.from_function_call(
                            name=tool_call.function.name,
                            args=args
                        ))
                    
                    gemini_messages.append(types.Content(
                        role="model",
                        parts=parts
                    ))
                else:
                    gemini_messages.append(types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=message.content)]
                    ))
            elif message.role == "tool":
                # Convert tool response to Gemini format
                # Gemini requires a non-empty name for function_response
                tool_name = message.name
                if not tool_name:
                    # Fallback: try to extract tool name from tool_call_id or use a default
                    if message.tool_call_id:
                        # Try to find the corresponding tool call in previous messages
                        for prev_msg in reversed(messages):
                            if prev_msg.role == "assistant" and prev_msg.tool_calls:
                                for tool_call in prev_msg.tool_calls:
                                    if tool_call.id == message.tool_call_id:
                                        tool_name = tool_call.function.name
                                        break
                                if tool_name:
                                    break
                    
                    # If still no name found, use a default
                    if not tool_name:
                        tool_name = "unknown_function"
                
                gemini_messages.append(types.Content(
                    role="user",
                    parts=[types.Part.from_function_response(
                        name=tool_name,
                        response={"result": message.content}
                    )]
                ))
        
        return system_content, gemini_messages

    def _sanitize_gemini_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Remove fields that are not supported by Gemini function declarations."""
        if not isinstance(schema, dict):
            return schema

        clean_schema = schema.copy()
        # Remove fields that Gemini API doesn't support
        for key in ["additionalProperties", "additional_properties", "title", "$schema"]:
            clean_schema.pop(key, None)

        if "properties" in clean_schema and isinstance(clean_schema["properties"], dict):
            clean_schema["properties"] = {
                name: self._sanitize_gemini_schema(value) for name, value in clean_schema["properties"].items()
            }
        if "items" in clean_schema:
            clean_schema["items"] = self._sanitize_gemini_schema(clean_schema["items"])

        return clean_schema
    
    def _convert_tools_to_gemini(self, tools: List[Dict]) -> List:
        """Convert OpenAI/Anthropic tool format to Gemini format."""
        gemini_tools = []
        
        if tools:
            function_declarations = []
            for tool in tools:
                if 'function' in tool:
                    func = tool['function']
                    parameters = self._sanitize_gemini_schema(func.get('parameters', {}))
                    function_declarations.append(types.FunctionDeclaration(
                        name=func.get('name'),
                        description=func.get('description'),
                        parameters=parameters
                    ))
            
            if function_declarations:
                gemini_tools.append(types.Tool(function_declarations=function_declarations))
        
        return gemini_tools
    
    async def chat(self, messages: List[Message], **kwargs) -> LLMResponse:
        """Send chat request to Gemini."""
        if not self.client:
            raise ProviderError("gemini", "Provider not initialized")
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            system_content, user_message = self._convert_messages(messages)
            
            # Extract parameters
            model = kwargs.get('model', self.model)
            max_tokens = kwargs.get('max_tokens', self.max_tokens)
            temperature = kwargs.get('temperature', self.temperature)
            response_modalities = kwargs.get('response_modalities')
            
            # Build request content
            if isinstance(user_message, str):
                contents = [types.Part.from_text(text=user_message)]
            else:
                contents = [user_message]
            
            # Generate configuration
            generate_config = types.GenerateContentConfig(
                max_output_tokens=max_tokens,
                temperature=temperature
            )
            
            # Add system instruction if available
            if system_content:
                generate_config.system_instruction = system_content
            
            # Add response modalities if specified
            if response_modalities:
                generate_config.response_modalities = response_modalities
            
            # Check for structured output requirements
            if "IMPORTANT INSTRUCTION" in system_content and "JSON format" in system_content:
                schema = {
                    "type": "object",
                    "properties": {
                        "response": {
                            "type": "string",
                            "description": "Response content to the user"
                        },
                        "should_hand_off": {
                            "type": "boolean",
                            "description": "Whether the conversation should be handed off to a design expert"
                        }
                    },
                    "required": ["response", "should_hand_off"],
                    "propertyOrdering": ["should_hand_off", "response"]
                }
                generate_config.response_schema = schema
                generate_config.response_mime_type = 'application/json'
            
            # Send request
            response = self.client.models.generate_content(
                model=model,
                contents=contents,
                config=generate_config
            )
            
            duration = asyncio.get_event_loop().time() - start_time
            return self._convert_response(response, duration)
            
        except Exception as e:
            await self._handle_error(e)
    
    async def chat_stream(self, messages: List[Message],callbacks: Optional[List] = None, **kwargs) -> AsyncIterator[LLMResponseChunk]:
        """Send streaming chat request to Gemini with callback support. 
        Yields:
            LLMResponseChunk: Structured streaming response chunks
        """
        if not self.client:
            raise ProviderError("gemini", "Provider not initialized")

        # Create callback manager
        callback_manager = CallbackManager.from_callbacks(callbacks)
        run_id = uuid4()
        
        try:
            system_content, user_message = self._convert_messages(messages)
            
            # Extract parameters
            model = kwargs.get('model', self.model)
            max_tokens = kwargs.get('max_tokens', self.max_tokens)
            temperature = kwargs.get('temperature', self.temperature)
            
            # Trigger on_llm_start callback
            await callback_manager.on_llm_start(run_id=run_id,messages=messages,model=model,provider="gemini")
            
            # Build request content
            if isinstance(user_message, str):
                contents = [types.Part.from_text(text=user_message)]
            else:
                contents = [user_message]
            
            # Generate configuration
            generate_config = types.GenerateContentConfig(
                max_output_tokens=max_tokens,
                temperature=temperature
            )
            
            if system_content:
                generate_config.system_instruction = system_content
            
            # Process streaming response
            full_content = ""
            chunk_index = 0
            finish_reason = None
            usage_data = None
            
            # Send streaming request
            stream = self.client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=generate_config,
                **{k: v for k, v in kwargs.items() 
                   if k not in ['model', 'max_tokens', 'temperature', 'callbacks']}
            )
            
            for part_response in stream:
                if part_response.candidates and part_response.candidates[0].content.parts:
                    chunk = part_response.candidates[0].content.parts[0].text
                    if chunk:
                        full_content += chunk
                        
                        # Trigger on_llm_new_token callback
                        await callback_manager.on_llm_new_token(
                            token=chunk,
                            run_id=run_id
                        )
                        
                        # Extract finish reason
                        if (part_response.candidates and 
                            part_response.candidates[0].finish_reason):
                            finish_reason = str(part_response.candidates[0].finish_reason)
                        
                        # Extract usage stats if available
                        if hasattr(part_response, 'usage_metadata') and part_response.usage_metadata:
                            usage_data = {
                                "prompt_tokens": part_response.usage_metadata.prompt_token_count,
                                "completion_tokens": part_response.usage_metadata.candidates_token_count,
                                "total_tokens": part_response.usage_metadata.total_token_count
                            }
                        
                        # Build response chunk
                        response_chunk = LLMResponseChunk(
                            content=full_content,
                            delta=chunk,
                            provider="gemini",
                            model=model,
                            finish_reason=finish_reason,
                            tool_calls=[],
                            usage=usage_data,
                            metadata={
                                "chunk_index": chunk_index,
                                "finish_reason": finish_reason
                            },
                            chunk_index=chunk_index
                        )
                        chunk_index += 1
                        yield response_chunk
            
            # Trigger on_llm_end callback
            final_response = LLMResponse(
                content=full_content,
                provider="gemini",
                model=model,
                finish_reason=finish_reason or "stop",
                native_finish_reason=finish_reason or "stop",
                tool_calls=[],
                usage=usage_data,
                metadata={}
            )
            await callback_manager.on_llm_end(
                response=final_response,
                run_id=run_id
            )
                            
        except Exception as e:
            await callback_manager.on_llm_error(
                error=e,
                run_id=run_id
            )
            await self._handle_error(e)
    
    async def completion(self, prompt: str, **kwargs) -> LLMResponse:
        """Send completion request to Gemini."""
        # Convert to chat format
        messages = [Message(role="user", content=prompt)]
        return await self.chat(messages, **kwargs)
    
    async def chat_with_tools(self, messages: List[Message], tools: List[Dict], **kwargs) -> LLMResponse:
        """Send chat request with tools to Gemini using native function calling."""
        if not self.client:
            raise ProviderError("gemini", "Provider not initialized")
        
        try:
            start_time = asyncio.get_event_loop().time()
            
            # Convert messages to Gemini format
            system_content, gemini_messages = self._convert_messages_for_tools(messages)
            
            # Convert tools to Gemini format
            gemini_tools = self._convert_tools_to_gemini(tools)
            
            # Extract parameters
            model = kwargs.get('model', self.model)
            max_tokens = kwargs.get('max_tokens', self.max_tokens)
            temperature = kwargs.get('temperature', self.temperature)
            
            # Generate configuration
            generate_config = types.GenerateContentConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
                tools=gemini_tools
            )
            
            # Add system instruction if available
            if system_content:
                generate_config.system_instruction = system_content
            
            # Send request
            response = self.client.models.generate_content(
                model=model,
                contents=gemini_messages,
                config=generate_config
            )
            
            duration = asyncio.get_event_loop().time() - start_time
            return self._convert_tool_response(response, duration)
            
        except Exception as e:
            await self._handle_error(e)
    
    def _convert_response(self, response, duration: float) -> LLMResponse:
        """Convert Gemini response to standardized LLMResponse."""
        content = ""
        response_text = ""
        image_paths = []
        tool_calls = []
        
        # Check if there are candidate results
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "content") and candidate.content:
                # Iterate through all parts
                for part in candidate.content.parts:
                    # Check if there is text content
                    if hasattr(part, "text") and part.text:
                        if content:
                            content += "\n" + part.text
                        else:
                            content = part.text
                        response_text = content
                    # Check if there is image content
                    elif hasattr(part, "inline_data"):
                        # Save image data
                        image_data = {
                            "mime_type": getattr(part.inline_data, "mime_type", "image/jpeg"),
                            "data": getattr(part.inline_data, "data", b"")
                        }
                        
                        # Save image to local storage
                        output_dir = "runtime-image-output"
                        os.makedirs(output_dir, exist_ok=True)
                        
                        timestamp = int(time.time())
                        ext = image_data['mime_type'].split('/')[-1]
                        filename = f"gemini_image_{timestamp}.{ext}"
                        filepath = os.path.join(output_dir, filename)
                        
                        try:
                            with open(filepath, "wb") as f:
                                f.write(image_data['data'])
                            
                            image_paths.append({
                                "filepath": filepath,
                                "mime_type": image_data['mime_type']
                            })
                            
                            # Add to tool calls for compatibility
                            tool_calls.append({
                                "type": "image",
                                "image": {
                                    "mime_type": image_data["mime_type"],
                                    "data": image_data["data"]
                                }
                            })
                            
                            # Update content
                            if content:
                                content += f"\n[Generated image saved to: {filepath}]"
                            else:
                                content = f"[Generated image saved to: {filepath}]"
                            response_text = content
                            
                        except Exception as e:
                            logger.error(f"Failed to save image: {str(e)}")
        
        # If no content was obtained and there were no candidates, fall back to response.text
        if (
            not content
            and (not hasattr(response, "candidates") or not response.candidates)
            and hasattr(response, "text")
        ):
            response_text = response.text
            content = response_text
        
        # Default content for image responses
        if not content and image_paths:
            content = "【Image response】"
        
        return LLMResponse(
            content=content or "",
            provider="gemini",
            model=self.model,
            finish_reason="stop",  # Gemini doesn't provide detailed finish reasons
            native_finish_reason="stop",
            tool_calls=[],  # Will be populated by _convert_tool_response for tool calls
            duration=duration,
            metadata={
                "image_paths": image_paths,
                "has_images": len(image_paths) > 0
            }
        )
    
    def _convert_tool_response(self, response, duration: float) -> LLMResponse:
        """Convert Gemini tool response to standardized LLMResponse."""
        content = ""
        tool_calls = []
        finish_reason = "stop"
        
        # Check if there are candidate results
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, "content") and candidate.content:
                # Iterate through all parts
                for part in candidate.content.parts:
                    # Check if there is text content
                    if hasattr(part, "text") and part.text:
                        if content:
                            content += "\n" + part.text
                        else:
                            content = part.text
                    # Check if there is a function call
                    elif hasattr(part, "function_call") and part.function_call:
                        # Convert Gemini function call to our ToolCall format
                        function_call = part.function_call
                        
                        # Generate a unique ID for the tool call
                        import uuid
                        tool_call_id = f"call_{uuid.uuid4().hex[:8]}"
                        
                        # Convert arguments to JSON string
                        import json
                        arguments_json = json.dumps(function_call.args) if function_call.args else "{}"
                        
                        tool_call = ToolCall(
                            id=tool_call_id,
                            type="function",
                            function=Function(
                                name=function_call.name,
                                arguments=arguments_json
                            )
                        )
                        tool_calls.append(tool_call)
                        finish_reason = "tool_calls"
        
        # If no content was obtained and there were no candidates, fall back to response.text
        if (
            not content
            and (not hasattr(response, "candidates") or not response.candidates)
            and hasattr(response, "text")
        ):
            content = response.text
        
        return LLMResponse(
            content=content or "",
            provider="gemini",
            model=self.model,
            finish_reason=finish_reason,
            native_finish_reason=finish_reason,
            tool_calls=tool_calls,
            duration=duration,
            metadata={}
        )
    
    def get_metadata(self) -> ProviderMetadata:
        """Get Gemini provider metadata."""
        return ProviderMetadata(
            name="gemini",
            version="1.0.0",
            capabilities=[
                ProviderCapability.CHAT,
                ProviderCapability.COMPLETION,
                ProviderCapability.STREAMING,
                ProviderCapability.TOOLS,
                ProviderCapability.IMAGE_GENERATION,
                ProviderCapability.VISION
            ],
            max_tokens=self.max_tokens,
            supports_system_messages=True,
            rate_limits={
                "requests_per_minute": 60,
                "tokens_per_minute": 32000
            }
        )
    
    async def health_check(self) -> bool:
        """Check if Gemini provider is healthy."""
        if not self.client:
            return False
        
        try:
            # Simple test request
            contents = [types.Part.from_text(text="test")]
            config = types.GenerateContentConfig(max_output_tokens=1)
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config
            )
            return True
        except Exception as e:
            logger.warning(f"Gemini health check failed: {e}")
            return False
    
    async def cleanup(self) -> None:
        """Cleanup Gemini provider resources."""
        # Gemini client doesn't require explicit cleanup
        self.client = None
        logger.info("Gemini provider cleaned up")
    
    async def _handle_error(self, error: Exception) -> None:
        """Handle and convert Gemini errors to standardized errors."""
        error_str = str(error).lower()
        
        if "authentication" in error_str or "api key" in error_str:
            raise AuthenticationError("gemini", context={"original_error": str(error)})
        elif "quota" in error_str or "rate limit" in error_str:
            raise RateLimitError("gemini", context={"original_error": str(error)})
        elif "model" in error_str and "not found" in error_str:
            raise ModelNotFoundError("gemini", self.model, context={"original_error": str(error)})
        elif "timeout" in error_str or "connection" in error_str:
            raise NetworkError("gemini", "Network error", original_error=error)
        else:
            raise ProviderError("gemini", f"Request failed: {str(error)}", original_error=error)
