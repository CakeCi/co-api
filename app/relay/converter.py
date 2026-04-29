try:
    import orjson as json
    def _dumps(obj, **kwargs) -> str:
        return json.dumps(obj, **kwargs).decode('utf-8')
except ImportError:
    import json
    def _dumps(obj, **kwargs) -> str:
        return json.dumps(obj, **kwargs)
import uuid
from typing import Any, Dict, List, Optional

class APIConverter:
    """API 格式转换器：支持 Anthropic、OpenAI、Bedrock、Gemini 之间的转换"""
    
    @staticmethod
    def generate_id() -> str:
        return str(uuid.uuid4())
    
    # ==================== Anthropic → OpenAI ====================
    
    @staticmethod
    def anthropic_to_openai_request(body: Dict[str, Any]) -> Dict[str, Any]:
        """Anthropic Messages API → OpenAI Chat Completions API"""
        result = {
            "model": body.get("model", "claude-3-opus-20240229"),
            "messages": []
        }
        
        # 处理 system prompt
        if "system" in body:
            system_content = body["system"]
            if isinstance(system_content, str):
                result["messages"].append({
                    "role": "system",
                    "content": system_content
                })
            elif isinstance(system_content, list):
                # Anthropic 的 system 可以是 content blocks
                text_parts = []
                for block in system_content:
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                if text_parts:
                    result["messages"].append({
                        "role": "system",
                        "content": "\n".join(text_parts)
                    })
        
        # 处理 messages
        for msg in body.get("messages", []):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if isinstance(content, str):
                result["messages"].append({
                    "role": role,
                    "content": content
                })
            elif isinstance(content, list):
                # Anthropic content blocks
                text_parts = []
                for block in content:
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif block.get("type") == "image":
                        # 处理图片（简化处理）
                        pass
                if text_parts:
                    result["messages"].append({
                        "role": role,
                        "content": "\n".join(text_parts)
                    })
        
        # 复制其他参数
        if "max_tokens" in body:
            result["max_tokens"] = body["max_tokens"]
        if "temperature" in body:
            result["temperature"] = body["temperature"]
        if "top_p" in body:
            result["top_p"] = body["top_p"]
        if "stream" in body:
            result["stream"] = body["stream"]
        if "stop" in body:
            result["stop"] = body["stop"]
        
        return result
    
    @staticmethod
    def openai_to_anthropic_request(body: Dict[str, Any]) -> Dict[str, Any]:
        """OpenAI Chat Completions → Anthropic Messages API"""
        result = {
            "model": body.get("model", "claude-3-opus-20240229"),
            "messages": []
        }
        
        # 提取 system prompt
        system_content = []
        for msg in body.get("messages", []):
            if msg.get("role") == "system":
                content = msg.get("content", "")
                if isinstance(content, str):
                    system_content.append(content)
                elif isinstance(content, list):
                    for block in content:
                        if block.get("type") == "text":
                            system_content.append(block.get("text", ""))
        
        if system_content:
            result["system"] = "\n".join(system_content)
        
        tool_result_ids = {
            msg.get("tool_call_id")
            for msg in body.get("messages", [])
            if msg.get("role") == "tool" and msg.get("tool_call_id")
        }

        # 处理非 system 消息
        seen_tool_use_ids = set()
        for msg in body.get("messages", []):
            role = msg.get("role", "user")
            if role == "system":
                continue
            
            anthropic_msg = {"role": role if role in ("user", "assistant") else "user"}
            
            if role == "assistant" and msg.get("tool_calls"):
                # Assistant message with tool calls
                blocks = []
                content = msg.get("content")
                if content:
                    if isinstance(content, str):
                        blocks.append({"type": "text", "text": content})
                    elif isinstance(content, list):
                        for block in content:
                            if block.get("type") == "text":
                                blocks.append({"type": "text", "text": block.get("text", "")})
                for tool_call in msg["tool_calls"]:
                    if tool_call.get("type") == "function":
                        tool_call_id = tool_call.get("id", "")
                        if not tool_call_id or tool_call_id not in tool_result_ids:
                            # Anthropic rejects assistant tool_use blocks without matching tool_result.
                            continue
                        func = tool_call.get("function", {})
                        arguments_str = func.get("arguments", "{}")
                        try:
                            arguments = json.loads(arguments_str)
                        except json.JSONDecodeError:
                            arguments = {}
                        blocks.append({
                            "type": "tool_use",
                            "id": tool_call_id,
                            "name": func.get("name", ""),
                            "input": arguments
                        })
                        if tool_call_id:
                            seen_tool_use_ids.add(tool_call_id)
                anthropic_msg["content"] = blocks
            elif role == "tool":
                # Tool result message -> Anthropic user message with tool_result
                if msg.get("tool_call_id") not in seen_tool_use_ids:
                    # Anthropic rejects orphan tool_result blocks when history was truncated.
                    continue
                anthropic_msg["role"] = "user"
                tool_call_id = msg.get("tool_call_id", "")
                content = msg.get("content", "")
                anthropic_msg["content"] = [{
                    "type": "tool_result",
                    "tool_use_id": tool_call_id,
                    "content": content if isinstance(content, str) else str(content)
                }]
            else:
                content = msg.get("content", "")
                if isinstance(content, str):
                    anthropic_msg["content"] = content
                elif isinstance(content, list):
                    # OpenAI content blocks → Anthropic content blocks
                    blocks = []
                    for block in content:
                        if block.get("type") == "text":
                            blocks.append({
                                "type": "text",
                                "text": block.get("text", "")
                            })
                        elif block.get("type") == "image_url":
                            image_url = block.get("image_url", {}).get("url", "")
                            # Reject non-standard references like clipboard which upstream text models can't read
                            if image_url.lower().strip().startswith("clipboard"):
                                raise ValueError("Unsupported image reference: clipboard")
                            if image_url.startswith("data:"):
                                # Parse data URI: data:image/<type>;base64,<data>
                                header, _, data = image_url.partition(",")
                                if not data:
                                    data = image_url
                                media_type = "image/png"
                                if "image/jpeg" in header or "image/jpg" in header:
                                    media_type = "image/jpeg"
                                elif "image/webp" in header:
                                    media_type = "image/webp"
                                elif "image/gif" in header:
                                    media_type = "image/gif"
                                blocks.append({
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": media_type,
                                        "data": data
                                    }
                                })
                            else:
                                blocks.append({
                                    "type": "image",
                                    "source": {
                                        "type": "url",
                                        "url": image_url
                                    }
                                })
                    anthropic_msg["content"] = blocks
                else:
                    anthropic_msg["content"] = str(content)
            
            result["messages"].append(anthropic_msg)
        
        # 如果没有消息，添加一个空的 user 消息
        if not result["messages"]:
            result["messages"].append({"role": "user", "content": "Hello"})
        result["messages"] = APIConverter._merge_consecutive_messages(result["messages"])
        
        # 复制其他参数
        if "max_tokens" in body:
            result["max_tokens"] = body["max_tokens"]
        else:
            result["max_tokens"] = 4096
        if "temperature" in body:
            result["temperature"] = body["temperature"]
        if "top_p" in body:
            result["top_p"] = body["top_p"]
        if "stream" in body:
            result["stream"] = body["stream"]
        if "stop" in body:
            result["stop_sequences"] = body["stop"] if isinstance(body["stop"], list) else [body["stop"]]
        
        # 转换 tools 参数
        if "tools" in body:
            anthropic_tools = []
            for tool in body["tools"]:
                if tool.get("type") == "function":
                    func = tool.get("function", {})
                    anthropic_tools.append({
                        "name": func.get("name", ""),
                        "description": func.get("description", ""),
                        "input_schema": func.get("parameters", {"type": "object", "properties": {}})
                    })
            if anthropic_tools:
                result["tools"] = anthropic_tools
        
        # 转换 tool_choice 参数
        if "tool_choice" in body:
            tc = body["tool_choice"]
            if tc == "auto":
                result["tool_choice"] = {"type": "auto"}
            elif tc == "any":
                result["tool_choice"] = {"type": "any"}
            elif tc == "none":
                result["tool_choice"] = {"type": "none"}
            elif isinstance(tc, dict) and tc.get("type") == "function":
                result["tool_choice"] = {
                    "type": "tool",
                    "name": tc.get("function", {}).get("name", "")
                }

        # Map OpenAI reasoning_effort → Anthropic thinking
        if "reasoning_effort" in body and "thinking" not in body:
            effort_map = {"low": 1024, "medium": 4096, "high": 16000}
            budget = effort_map.get(str(body["reasoning_effort"]).lower(), 4096)
            result["thinking"] = {"type": "enabled", "budget_tokens": budget}
        if "reasoning_summary" in body:
            # reasoning_summary: "auto" → map to Anthropic's thinking metadata
            pass

        return result

    @staticmethod
    def _merge_consecutive_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Anthropic expects a clean user/assistant sequence; merge adjacent same-role turns."""
        merged: List[Dict[str, Any]] = []
        for msg in messages:
            if not msg.get("content"):
                continue
            if merged and merged[-1].get("role") == msg.get("role"):
                merged[-1]["content"] = APIConverter._append_content(merged[-1].get("content", ""), msg.get("content", ""))
            else:
                merged.append(msg)
        return merged or [{"role": "user", "content": "Hello"}]

    @staticmethod
    def _append_content(left: Any, right: Any) -> Any:
        left_blocks = left if isinstance(left, list) else ([{"type": "text", "text": left}] if left else [])
        right_blocks = right if isinstance(right, list) else ([{"type": "text", "text": right}] if right else [])
        return left_blocks + right_blocks
    
    @staticmethod
    def openai_to_anthropic_response(body: Dict[str, Any]) -> Dict[str, Any]:
        """OpenAI Chat Completions → Anthropic Messages"""
        choice = body.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage = body.get("usage", {})
        
        result = {
            "id": f"msg_{APIConverter.generate_id().replace('-', '')}",
            "type": "message",
            "role": "assistant",
            "model": body.get("model", "claude-3-opus-20240229"),
            "content": [],
            "stop_reason": APIConverter._map_finish_reason(choice.get("finish_reason")),
            "usage": {
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0)
            }
        }
        
        # 处理 content
        content = message.get("content", "")
        if content:
            result["content"].append({
                "type": "text",
                "text": content
            })
        
        return result
    
    @staticmethod
    def anthropic_to_openai_response(body: Dict[str, Any]) -> Dict[str, Any]:
        """Anthropic Messages → OpenAI Chat Completions
        
        支持标准 Anthropic tool_use blocks 以及 text 中嵌入的 XML <tool_use>。
        """
        import re
        
        content_blocks = body.get("content", [])
        content_text = ""
        tool_calls = []
        
        for block in content_blocks:
            if block.get("type") == "text":
                text = block.get("text", "")
                # 检查 text 中是否包含 XML 格式的 tool_use（讯飞格式）
                xml_tools = APIConverter._parse_xml_tool_use(text)
                if xml_tools:
                    # 把 XML 部分从 text 中移除
                    clean_text = APIConverter._remove_xml_tool_use(text)
                    if clean_text.strip():
                        content_text += clean_text
                    tool_calls.extend(xml_tools)
                else:
                    content_text += text
            elif block.get("type") == "tool_use":
                # 标准 Anthropic tool_use block
                tool_calls.append({
                    "id": block.get("id", f"call_{APIConverter.generate_id().replace('-', '')}"),
                    "type": "function",
                    "function": {
                        "name": block.get("name", ""),
                        "arguments": _dumps(block.get("input", {}))
                    }
                })
        
        usage = body.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        
        message = {
            "role": "assistant",
            "content": content_text if content_text else None
        }
        
        if tool_calls:
            message["tool_calls"] = tool_calls
        
        finish_reason = "tool_calls" if tool_calls else APIConverter._map_stop_reason(body.get("stop_reason"))
        
        result = {
            "id": body.get("id", f"chatcmpl_{APIConverter.generate_id().replace('-', '')}"),
            "object": "chat.completion",
            "created": int(__import__('time').time()),
            "model": body.get("model", "claude-3-opus-20240229"),
            "choices": [{
                "index": 0,
                "message": message,
                "finish_reason": finish_reason
            }],
            "usage": {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            }
        }
        
        return result
    
    @staticmethod
    def _parse_xml_tool_use(text: str) -> List[Dict[str, Any]]:
        """解析 text 中嵌入的 XML <tool_use> 块，返回 OpenAI tool_calls 格式列表"""
        import re
        tools = []
        # 匹配 <tool_use>...</tool_use> 块
        pattern = r'<tool_use>\s*<server_name>(.*?)</server_name>\s*<tool_name>(.*?)</tool_name>\s*<parameters>\s*(.*?)\s*</parameters>\s*</tool_use>'
        matches = re.findall(pattern, text, re.DOTALL)
        
        for idx, (server_name, tool_name, params_text) in enumerate(matches):
            # 解析参数: "key: value" 格式
            arguments = {}
            for line in params_text.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    arguments[key.strip()] = value.strip().strip('"').strip("'")
            
            tools.append({
                "id": f"call_{APIConverter.generate_id().replace('-', '')}_{idx}",
                "type": "function",
                "function": {
                    "name": tool_name.strip(),
                    "arguments": _dumps(arguments)
                }
            })
        
        return tools
    
    @staticmethod
    def _remove_xml_tool_use(text: str) -> str:
        """从 text 中移除 XML <tool_use> 块"""
        import re
        pattern = r'\s*<tool_use>\s*<server_name>.*?</server_name>\s*<tool_name>.*?</tool_name>\s*<parameters>\s*.*?\s*</parameters>\s*</tool_use>\s*'
        return re.sub(pattern, '\n\n', text, flags=re.DOTALL)
    
    @staticmethod
    def _map_stop_reason(reason: Optional[str]) -> Optional[str]:
        """映射 Anthropic stop_reason 到 OpenAI finish_reason"""
        mapping = {
            "end_turn": "stop",
            "max_tokens": "length",
            "tool_use": "tool_calls",
            "content_filter": "content_filter"
        }
        return mapping.get(reason, reason)
    
    @staticmethod
    def _map_finish_reason(reason: Optional[str]) -> Optional[str]:
        """映射 finish_reason"""
        mapping = {
            "stop": "end_turn",
            "length": "max_tokens",
            "tool_calls": "tool_use",
            "content_filter": "content_filter"
        }
        return mapping.get(reason, reason)
    
    # ==================== Anthropic SSE → OpenAI SSE ====================
    
    @staticmethod
    def anthropic_sse_to_openai_sse(chunk: str) -> str:
        """Anthropic SSE 流式响应 → OpenAI SSE 格式"""
        if not chunk.strip():
            return chunk
        
        lines = chunk.strip().split('\n')
        result_lines = []
        
        for line in lines:
            # Skip SSE comment lines (heartbeat/keepalive)
            if line.startswith(':'):
                continue
            # Skip Anthropic event: lines (OpenAI format doesn't need them)
            if line.startswith('event: '):
                if "ping" in line.lower():
                    # Skip ping event type entirely
                    continue
                continue
            
            if line.startswith('data: '):
                data = line[6:]
                try:
                    event = json.loads(data)
                    event_type = event.get("type", "")
                    
                    if event_type == "content_block_delta":
                        delta = event.get("delta", {})
                        if delta.get("type") == "text_delta":
                            openai_event = {
                                "choices": [{
                                    "delta": {
                                        "content": delta.get("text", "")
                                    },
                                    "index": 0,
                                    "finish_reason": None
                                }],
                                "object": "chat.completion.chunk"
                            }
                            result_lines.append(f"data: {_dumps(openai_event)}")
                    
                    elif event_type == "message_stop":
                        openai_event = {
                            "choices": [{
                                "delta": {},
                                "index": 0,
                                "finish_reason": "stop"
                            }],
                            "object": "chat.completion.chunk"
                        }
                        result_lines.append(f"data: {_dumps(openai_event)}")
                        result_lines.append("data: [DONE]")
                    
                    elif event_type == "message_start":
                        message = event.get("message", {})
                        openai_event = {
                            "id": message.get("id", ""),
                            "model": message.get("model", ""),
                            "choices": [{
                                "delta": {"role": "assistant"},
                                "index": 0,
                                "finish_reason": None
                            }],
                            "object": "chat.completion.chunk"
                        }
                        result_lines.append(f"data: {_dumps(openai_event)}")
                    
                    elif event_type == "content_block_start":
                        # 忽略 content_block_start，不输出到 OpenAI 格式
                        pass
                    
                    elif event_type == "content_block_stop":
                        # 忽略 content_block_stop
                        pass
                    
                    elif event_type == "message_delta":
                        # 处理 usage 信息
                        usage = event.get("usage", {})
                        openai_event = {
                            "choices": [{
                                "delta": {},
                                "index": 0,
                                "finish_reason": None
                            }],
                            "object": "chat.completion.chunk",
                            "usage": {
                                "prompt_tokens": usage.get("input_tokens", 0),
                                "completion_tokens": usage.get("output_tokens", 0),
                                "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                            }
                        }
                        result_lines.append(f"data: {_dumps(openai_event)}")
                    
                    elif event_type == "ping":
                        # Silently drop upstream ping/heartbeat events
                        continue
                    else:
                        result_lines.append(line)
                        
                except json.JSONDecodeError:
                    result_lines.append(line)
            else:
                result_lines.append(line)
        
        # SSE 事件之间需要空行分隔
        events = []
        for line in result_lines:
            events.append(line)
            events.append("")  # 空行分隔事件
        result = '\n'.join(events)
        # 确保结果以 \n\n 结尾（SSE 事件结束标记）
        if result and not result.endswith('\n\n'):
            result += '\n\n'
        return result
    
    @staticmethod
    def openai_sse_to_anthropic_sse(chunk: str) -> str:
        """OpenAI SSE → Anthropic SSE"""
        if not chunk.strip():
            return chunk
        
        lines = chunk.strip().split('\n')
        result_lines = []
        
        for line in lines:
            if line.startswith('data: '):
                data = line[6:]
                if data == "[DONE]":
                    anthropic_event = {
                        "type": "message_stop"
                    }
                    result_lines.append(f"data: {_dumps(anthropic_event)}")
                    continue
                
                try:
                    event = json.loads(data)
                    choice = event.get("choices", [{}])[0]
                    delta = choice.get("delta", {})
                    finish_reason = choice.get("finish_reason")
                    
                    if finish_reason:
                        anthropic_event = {
                            "type": "message_stop"
                        }
                        result_lines.append(f"data: {_dumps(anthropic_event)}")
                    elif "content" in delta and delta["content"]:
                        anthropic_event = {
                            "type": "content_block_delta",
                            "index": 0,
                            "delta": {
                                "type": "text_delta",
                                "text": delta["content"]
                            }
                        }
                        result_lines.append(f"data: {_dumps(anthropic_event)}")
                    elif "role" in delta:
                        anthropic_event = {
                            "type": "message_start",
                            "message": {
                                "id": event.get("id", f"msg_{APIConverter.generate_id().replace('-', '')}"),
                                "type": "message",
                                "role": "assistant",
                                "model": event.get("model", ""),
                                "content": [],
                                "stop_reason": None,
                                "stop_sequence": None,
                                "usage": {"input_tokens": 0, "output_tokens": 0}
                            }
                        }
                        result_lines.append(f"data: {_dumps(anthropic_event)}")
                    
                except json.JSONDecodeError:
                    result_lines.append(line)
            else:
                result_lines.append(line)
        
        result = '\n'.join(result_lines)
        if result and not result.endswith('\n\n'):
            result += '\n\n'
        return result
    
    # ==================== Gemini → OpenAI ====================
    
    @staticmethod
    def gemini_to_openai_request(body: Dict[str, Any]) -> Dict[str, Any]:
        """Gemini API → OpenAI Chat Completions"""
        result = {
            "model": body.get("model", "gemini-pro"),
            "messages": []
        }
        
        # Gemini 使用 contents 字段
        for content in body.get("contents", []):
            role = content.get("role", "user")
            parts = content.get("parts", [])
            
            text_parts = []
            for part in parts:
                if "text" in part:
                    text_parts.append(part["text"])
            
            if text_parts:
                result["messages"].append({
                    "role": role if role != "model" else "assistant",
                    "content": "\n".join(text_parts)
                })
        
        # 复制生成参数
        generation_config = body.get("generationConfig", {})
        if "maxOutputTokens" in generation_config:
            result["max_tokens"] = generation_config["maxOutputTokens"]
        if "temperature" in generation_config:
            result["temperature"] = generation_config["temperature"]
        if "topP" in generation_config:
            result["top_p"] = generation_config["topP"]
        
        return result
    
    @staticmethod
    def openai_to_gemini_response(body: Dict[str, Any]) -> Dict[str, Any]:
        """OpenAI Chat Completions → Gemini API"""
        choice = body.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage = body.get("usage", {})
        
        return {
            "candidates": [{
                "content": {
                    "parts": [{"text": message.get("content", "")}],
                    "role": "model"
                },
                "finishReason": choice.get("finish_reason", "STOP").upper(),
                "index": 0,
                "safetyRatings": []
            }],
            "usageMetadata": {
                "promptTokenCount": usage.get("prompt_tokens", 0),
                "candidatesTokenCount": usage.get("completion_tokens", 0),
                "totalTokenCount": usage.get("total_tokens", 0)
            }
        }
    
    # ==================== Bedrock → OpenAI ====================
    
    @staticmethod
    def bedrock_to_openai_request(body: Dict[str, Any]) -> Dict[str, Any]:
        """Bedrock API → OpenAI Chat Completions"""
        result = {
            "model": body.get("modelId", "anthropic.claude-3-opus-20240229-v1:0"),
            "messages": []
        }
        
        # Bedrock 使用 messages 数组
        for msg in body.get("messages", []):
            role = msg.get("role", "user")
            content = msg.get("content", [])
            
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                if text_parts:
                    result["messages"].append({
                        "role": role,
                        "content": "\n".join(text_parts)
                    })
            elif isinstance(content, str):
                result["messages"].append({
                    "role": role,
                    "content": content
                })
        
        # 复制参数
        if "max_tokens" in body:
            result["max_tokens"] = body["max_tokens"]
        if "temperature" in body:
            result["temperature"] = body["temperature"]
        if "top_p" in body:
            result["top_p"] = body["top_p"]
        if "stop_sequences" in body:
            result["stop"] = body["stop_sequences"]
        
        return result
    
    @staticmethod
    def openai_to_bedrock_response(body: Dict[str, Any]) -> Dict[str, Any]:
        """OpenAI Chat Completions → Bedrock API"""
        choice = body.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage = body.get("usage", {})
        
        return {
            "id": body.get("id", ""),
            "type": "message",
            "role": "assistant",
            "model": body.get("model", ""),
            "content": [{"type": "text", "text": message.get("content", "")}],
            "stop_reason": APIConverter._map_finish_reason(choice.get("finish_reason")),
            "usage": {
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0)
            }
        }


class AnthropicSSEToOpenAIConverter:
    """有状态的 Anthropic SSE → OpenAI SSE 转换器，支持 tool_use 流式转换"""

    def __init__(self):
        self.message_id = None
        self.model = None
        self.block_info = {}  # index -> {type, tool_call_index, id, name}
        self.tool_call_counter = 0
        self.last_finish_reason = None
        self.input_tokens = 0  # 保存 message_start 中的 input_tokens
        self.output_tokens = 0  # 保存 message_delta 中的 output_tokens

    def convert(self, chunk: str) -> str:
        if not chunk.strip():
            return chunk

        lines = chunk.strip().split('\n')
        result_lines = []

        for line in lines:
            # Skip SSE comment lines (heartbeat/keepalive)
            if line.startswith(':'):
                continue
            # Skip Anthropic event: lines (OpenAI format doesn't need them)
            if line.startswith('event: '):
                if "ping" in line.lower():
                    # Skip ping event type entirely
                    continue
                continue

            if line.startswith('data: '):
                data = line[6:]
                try:
                    event = json.loads(data)
                    event_type = event.get("type", "")

                    if event_type == "message_start":
                        message = event.get("message", {})
                        self.message_id = message.get("id", "")
                        self.model = message.get("model", "")
                        # 保存 message_start 中的 input_tokens
                        usage = message.get("usage", {})
                        self.input_tokens = usage.get("input_tokens", 0) or usage.get("prompt_tokens", 0)
                        openai_event = {
                            "id": self.message_id,
                            "model": self.model,
                            "choices": [{
                                "delta": {"role": "assistant"},
                                "index": 0,
                                "finish_reason": None
                            }],
                            "object": "chat.completion.chunk"
                        }
                        result_lines.append(f"data: {_dumps(openai_event)}")

                    elif event_type == "content_block_start":
                        block = event.get("content_block", {})
                        index = event.get("index", 0)
                        block_type = block.get("type")
                        if block_type == "text":
                            self.block_info[index] = {"type": "text"}
                        elif block_type == "tool_use":
                            tool_call_index = self.tool_call_counter
                            self.tool_call_counter += 1
                            self.block_info[index] = {
                                "type": "tool_use",
                                "tool_call_index": tool_call_index,
                                "id": block.get("id", ""),
                                "name": block.get("name", "")
                            }
                            openai_event = {
                                "id": self.message_id,
                                "model": self.model,
                                "choices": [{
                                    "delta": {
                                        "tool_calls": [{
                                            "index": tool_call_index,
                                            "id": block.get("id", ""),
                                            "type": "function",
                                            "function": {
                                                "name": block.get("name", ""),
                                                "arguments": ""
                                            }
                                        }]
                                    },
                                    "index": 0,
                                    "finish_reason": None
                                }],
                                "object": "chat.completion.chunk"
                            }
                            result_lines.append(f"data: {_dumps(openai_event)}")

                    elif event_type == "content_block_delta":
                        index = event.get("index", 0)
                        delta = event.get("delta", {})
                        delta_type = delta.get("type", "")

                        if delta_type == "text_delta":
                            openai_event = {
                                "id": self.message_id,
                                "model": self.model,
                                "choices": [{
                                    "delta": {"content": delta.get("text", "")},
                                    "index": 0,
                                    "finish_reason": None
                                }],
                                "object": "chat.completion.chunk"
                            }
                            result_lines.append(f"data: {_dumps(openai_event)}")

                        elif delta_type == "input_json_delta":
                            block_info = self.block_info.get(index)
                            if block_info and block_info.get("type") == "tool_use":
                                tool_call_index = block_info["tool_call_index"]
                                openai_event = {
                                    "id": self.message_id,
                                    "model": self.model,
                                    "choices": [{
                                        "delta": {
                                            "tool_calls": [{
                                                "index": tool_call_index,
                                                "function": {
                                                    "arguments": delta.get("partial_json", "")
                                                }
                                            }]
                                        },
                                        "index": 0,
                                        "finish_reason": None
                                    }],
                                    "object": "chat.completion.chunk"
                                }
                                result_lines.append(f"data: {_dumps(openai_event)}")

                    elif event_type == "message_delta":
                        delta = event.get("delta", {})
                        stop_reason = delta.get("stop_reason")
                        finish_reason = None
                        if stop_reason == "tool_use":
                            finish_reason = "tool_calls"
                        elif stop_reason == "end_turn":
                            finish_reason = "stop"
                        elif stop_reason == "max_tokens":
                            finish_reason = "length"
                        elif stop_reason:
                            finish_reason = stop_reason

                        self.last_finish_reason = finish_reason

                        if finish_reason:
                            openai_event = {
                                "id": self.message_id,
                                "model": self.model,
                                "choices": [{
                                    "delta": {},
                                    "index": 0,
                                    "finish_reason": finish_reason
                                }],
                                "object": "chat.completion.chunk"
                            }
                            result_lines.append(f"data: {_dumps(openai_event)}")

                        # usage - 合并 message_start 的 input_tokens 和 message_delta 的 output_tokens
                        usage = event.get("usage", {})
                        delta_output = usage.get("output_tokens", 0)
                        if delta_output:
                            self.output_tokens = delta_output
                        if self.input_tokens or self.output_tokens:
                            total = self.input_tokens + self.output_tokens
                            usage_event = {
                                "id": self.message_id,
                                "model": self.model,
                                "choices": [],
                                "object": "chat.completion.chunk",
                                "usage": {
                                    "prompt_tokens": self.input_tokens,
                                    "completion_tokens": self.output_tokens,
                                    "total_tokens": total
                                }
                            }
                            result_lines.append(f"data: {_dumps(usage_event)}")

                    elif event_type == "message_stop":
                        # 如果 message_delta 已经发送过 finish_reason，这里不再重复发送
                        if not self.last_finish_reason:
                            openai_event = {
                                "id": self.message_id,
                                "model": self.model,
                                "choices": [{
                                    "delta": {},
                                    "index": 0,
                                    "finish_reason": "stop"
                                }],
                                "object": "chat.completion.chunk"
                            }
                            result_lines.append(f"data: {_dumps(openai_event)}")
                        result_lines.append("data: [DONE]")

                    elif event_type == "content_block_stop":
                        pass

                    elif event_type == "ping":
                        # Silently drop upstream ping/heartbeat events
                        continue
                    else:
                        result_lines.append(line)

                except json.JSONDecodeError:
                    result_lines.append(line)
            else:
                result_lines.append(line)

        # SSE 事件之间需要空行分隔
        events = []
        for line in result_lines:
            events.append(line)
            events.append("")  # 空行分隔事件
        result = '\n'.join(events)
        # 确保结果以 \n\n 结尾（SSE 事件结束标记）
        if result and not result.endswith('\n\n'):
            result += '\n\n'
        return result


# 便捷函数
anthropic_to_openai_request = APIConverter.anthropic_to_openai_request
openai_to_anthropic_request = APIConverter.openai_to_anthropic_request
openai_to_anthropic_response = APIConverter.openai_to_anthropic_response
anthropic_to_openai_response = APIConverter.anthropic_to_openai_response
openai_sse_to_anthropic_sse = APIConverter.openai_sse_to_anthropic_sse
anthropic_sse_to_openai_sse = APIConverter.anthropic_sse_to_openai_sse
gemini_to_openai_request = APIConverter.gemini_to_openai_request
openai_to_gemini_response = APIConverter.openai_to_gemini_response
bedrock_to_openai_request = APIConverter.bedrock_to_openai_request
openai_to_bedrock_response = APIConverter.openai_to_bedrock_response
