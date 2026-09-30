"""Builtin native tool history, with explicit opt-in hooks for protocol evaluation.

No text is parsed into executable tool calls. Completion probes are supplied by
trusted host code, never by a model response or provider configuration.
The checkpoint hook is experimental; production retains its existing summary policy.
"""

import copy
import json

ACTION_INSTRUCTION = (
    "When work remains, make the next structured tool call in this same response. "
    "A progress sentence may accompany that call; do not send a standalone promise "
    "to act. When the requested turn is finished, call final_answer directly, without "
    "first writing a separate final answer in prose."
)


def native_messages(messages):
    """Preserve native call IDs and tool results instead of flattening them to prose."""
    from smolagents.models import get_clean_message_list

    result = []
    for message in messages:
        if not isinstance(message, dict):
            message = json.loads(message.model_dump_json())
        message = copy.deepcopy(message)
        role = {"tool-call": "assistant", "tool-response": "user"}.get(
            message["role"], message["role"]
        )
        content = message.get("content")
        # Reuse the library's image encoder, but do not let its message cleaner
        # discard tool_calls/tool_call_id or merge different tool results.
        if isinstance(content, list):
            content = get_clean_message_list(
                [{"role": "user", "content": content}], convert_images_to_image_urls=True
            )[0]["content"]
            if role == "assistant":
                content = "\n".join(p.get("text", "") for p in content)
        row = {"role": role, "content": content}
        if message.get("tool_calls"):
            row["tool_calls"] = message["tool_calls"]
            for call in row["tool_calls"]:
                arguments = call["function"]["arguments"]
                if not isinstance(arguments, str):
                    call["function"]["arguments"] = json.dumps(arguments)
        if "tool_call_id" in message:
            row["tool_call_id"] = message["tool_call_id"]
        result.append(row)
    return result


def step_messages(step):
    """Read receipts captured from executed structured calls, never model prose."""
    if hasattr(step, "native_receipts"):
        messages = copy.deepcopy(step.native_receipts)
        if getattr(step, "error", None):
            for message in messages:
                if message["role"] == "tool" and str(message["content"]).startswith(
                    "Tool call or batch interrupted"
                ):
                    message["content"] += "\nRecorded error: " + str(step.error)[:24000]
        return messages
    return [json.loads(m.model_dump_json()) for m in step.to_messages()]


def agent_type(*, native_tools=False, checkpoint=False):
    """Construct only after the optional builtin-agent dependency is installed."""
    from smolagents import ToolCallingAgent
    from smolagents.agents import ToolOutput
    from smolagents.models import ChatMessage

    if not native_tools and not checkpoint:
        return ToolCallingAgent

    class ProtocolAgent(ToolCallingAgent):
        def write_memory_to_messages(self, summary_mode=False):
            if not native_tools:
                return super().write_memory_to_messages(summary_mode=summary_mode)
            messages = self.memory.system_prompt.to_messages(summary_mode=summary_mode)
            for step in self.memory.steps:
                messages.extend(step_messages(step))
            return messages

        def process_tool_calls(self, chat_message, memory_step):
            if not native_tools:
                yield from super().process_tool_calls(chat_message, memory_step)
                return
            calls = json.loads(chat_message.model_dump_json()).get("tool_calls") or []
            outputs = {}
            try:
                for event in super().process_tool_calls(chat_message, memory_step):
                    if isinstance(event, ToolOutput):
                        outputs[event.id] = event.observation
                    yield event
            finally:
                if calls:
                    memory_step.native_receipts = [
                        {
                            "role": "assistant",
                            "content": chat_message.content,
                            "tool_calls": calls,
                        },
                        *[
                            {
                                "role": "tool",
                                "tool_call_id": call["id"],
                                "content": outputs.get(
                                    call["id"],
                                    "Tool call or batch interrupted before its result "
                                    "was recorded. "
                                    "Inspect current state before retrying; success is unverified.",
                                ),
                            }
                            for call in calls
                        ],
                    ]

        def provide_final_answer(self, task):
            if not checkpoint:
                return super().provide_final_answer(task)
            from .workspace_agent import emit

            # The upstream max-step handler still records max_steps_error. This
            # is a saved-work checkpoint, never a successful or accepted result.
            emit("checkpoint", reason="action_limit", generated_summary=False)
            return ChatMessage(
                role="assistant",
                content=(
                    "Action limit reached. This turn is incomplete. Resume from saved files "
                    "and recorded tool results; verify pending work and required deliverables."
                ),
            )

    return ProtocolAgent
