from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, ToolMessage
import json
import logging


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]


class Agent:
    def __init__(self, model, tools, system=""):
        """
        model: a ChatOpenAI-like object with .invoke(messages) returning a Message with optional .tool_calls
        tools: list of Tool instances (with .name and .invoke(args))
        system: system prompt string
        """
        self.system_message = SystemMessage(content=system) if system else None
        # Build state graph: LLM -> check if needs action -> action -> LLM ...
        graph = StateGraph(AgentState)
        graph.add_node("llm", self.call_openai)
        graph.add_node("action", self.take_action)
        graph.add_conditional_edges(
            "llm", self.exists_action, {True: "action", False: END}
        )
        graph.add_edge("action", "llm")
        graph.set_entry_point("llm")
        self.graph = graph.compile()
        # Map tools by name
        self.tools = {t.name: t for t in tools}
        # Bind tools to model if supported
        try:
            self.model = model.bind_tools(tools)
        except Exception:
            self.model = model
        # Protect against infinite loops
        self.max_steps = 10

    def __call__(self, question_text: str, file_path: str | None) -> str:
        # Initialize messages
        messages = []
        if self.system_message:
            messages.append(self.system_message)
        # If a file is provided, inform the LLM that it can use file_tool
        if file_path:
            # It's better to give an absolute path so the LLM/tool can access
            messages.append(
                HumanMessage(
                    content=(
                        f"A file is available at local path: {file_path}. "
                        "You can inspect it by calling the 'file_tool' with args "
                        f"{{'path': '{file_path}', ...}}."
                    )
                )
            )
        # Finally, the actual question
        messages.append(HumanMessage(content=question_text))

        state = {"messages": messages}
        # The rest of the loop remains as before:
        steps = 0
        current_state = state
        while True:
            if steps >= self.max_steps:
                break
            out = self.call_openai(current_state)
            current_state["messages"] = out["messages"]
            if not self.exists_action(current_state):
                break
            out_action = self.take_action(current_state)
            for tm in out_action["messages"]:
                current_state["messages"].append(tm)
            steps += 1

        # Extract final assistant message, strip chain-of-thought, etc.
        final_content = ""
        for msg in reversed(current_state["messages"]):
            if not isinstance(msg, ToolMessage):
                final_content = getattr(msg, "content", "") or ""
                break
        # As before, if using FINAL ANSWER marker, extract it:
        marker = "FINAL ANSWER:"
        idx = final_content.upper().find(marker)
        if idx != -1:
            extracted = final_content[idx + len(marker) :].strip()
            return extracted
        return final_content.strip()

    def exists_action(self, state: AgentState) -> bool:
        # Look at last message: does it request a tool call?
        last = state["messages"][-1]
        tool_calls = getattr(last, "tool_calls", None)
        return bool(tool_calls)

    def call_openai(self, state: AgentState) -> AgentState:
        messages = state["messages"].copy()
        # Invoke LLM
        try:
            response = self.model.invoke(messages)
        except Exception as e:
            logging.error(f"LLM invocation failed: {e}")
            # Create a fallback message
            response = HumanMessage(content=f"Error invoking LLM: {e}")
        # Append
        new_msgs = state["messages"] + [response]
        return {"messages": new_msgs}

    def take_action(self, state: AgentState) -> AgentState:
        last = state["messages"][-1]
        tool_calls = getattr(last, "tool_calls", None)
        tool_msgs = []
        if tool_calls:
            for t in tool_calls:
                name = t.get("name")
                args = t.get("args", {})
                logging.info(f"Invoking tool: {name} with args: {args}")
                if name not in self.tools:
                    res = f"Error: unknown tool '{name}'"
                else:
                    # Ensure args is dict
                    if not isinstance(args, dict):
                        try:
                            args = json.loads(args)
                            if not isinstance(args, dict):
                                args = {"query": str(args)}
                        except Exception:
                            args = {"query": str(args)}
                    try:
                        res = self.tools[name].invoke(args)
                    except Exception as e:
                        res = f"Error during tool '{name}': {e}"
                # Create a ToolMessage so LLM sees it
                tm = ToolMessage(tool_call_id=t.get("id"), name=name, content=str(res))
                tool_msgs.append(tm)
        return {"messages": tool_msgs}
