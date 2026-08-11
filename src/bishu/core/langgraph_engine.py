"""LangGraph agent engine providing stateful graph orchestration & multi-agent workflow routing."""

import json
from typing import Dict, Any, List, TypedDict

try:
    from langgraph.graph import StateGraph, END
    HAS_LANGGRAPH = True
except Exception:
    HAS_LANGGRAPH = False
    END = "__end__"


class AgentState(TypedDict, total=False):
    """LangGraph state schema for multi-agent workflows."""
    user_input: str
    intent: str
    web_facts: str
    vision_facts: str
    action_result: str
    ai_reply: str
    conversation_history: List[Dict[str, str]]
    final_output: str


class LangGraphEngine:
    """Stateful LangGraph Agent Orchestrator for Laalaa AI Assistant."""

    def __init__(self, ai_engine=None, search_engine=None, automation_engine=None, vision_engine=None, code_agent=None):
        self.ai = ai_engine
        self.search = search_engine
        self.automation = automation_engine
        self.vision = vision_engine
        self.code_agent = code_agent
        self.compiled_graph = None

        if HAS_LANGGRAPH:
            self._build_langgraph()

    def _build_langgraph(self):
        """Construct official LangGraph StateGraph workflow."""
        try:
            workflow = StateGraph(AgentState)

            # Define graph nodes
            workflow.add_node("intent_router", self._node_router)
            workflow.add_node("search_node", self._node_search)
            workflow.add_node("vision_node", self._node_vision)
            workflow.add_node("automation_node", self._node_automation)
            workflow.add_node("code_node", self._node_code)
            workflow.add_node("llm_response_node", self._node_llm)

            # Set entry point
            workflow.set_entry_point("intent_router")

            # Conditional routing edges
            workflow.add_conditional_edges(
                "intent_router",
                self._route_decision,
                {
                    "search": "search_node",
                    "vision": "vision_node",
                    "automation": "automation_node",
                    "code": "code_node",
                    "chat": "llm_response_node",
                }
            )

            # Connect tool nodes to LLM node
            workflow.add_edge("search_node", "llm_response_node")
            workflow.add_edge("vision_node", "llm_response_node")
            workflow.add_edge("automation_node", END)
            workflow.add_edge("code_node", END)
            workflow.add_edge("llm_response_node", END)

            self.compiled_graph = workflow.compile()
            print("[LangGraphEngine] Official LangGraph StateGraph compiled successfully!")
        except Exception as e:
            print(f"[LangGraphEngine] LangGraph build info/fallback: {e}")
            self.compiled_graph = None

    def execute(self, user_input: str, history: List[Dict[str, str]] = None) -> str:
        """Execute stateful graph workflow for incoming user command."""
        initial_state: AgentState = {
            "user_input": user_input,
            "intent": "chat",
            "web_facts": "",
            "vision_facts": "",
            "action_result": "",
            "ai_reply": "",
            "conversation_history": history or [],
            "final_output": ""
        }

        # 1. Official LangGraph execution
        if HAS_LANGGRAPH and self.compiled_graph:
            try:
                final_state = self.compiled_graph.invoke(initial_state)
                output = final_state.get("final_output") or final_state.get("ai_reply") or final_state.get("action_result")
                if output:
                    return output
            except Exception as e:
                print(f"[LangGraphEngine] LangGraph runtime info/fallback: {e}")

        # 2. Resilient Graph Workflow Fallback Engine
        return self._run_custom_graph(initial_state)

    def _run_custom_graph(self, state: AgentState) -> str:
        """Resilient graph state machine runner."""
        # Node 1: Intent Router
        state = self._node_router(state)
        intent = state.get("intent", "chat")

        # Node 2: Route to specialized tool node
        if intent == "automation":
            state = self._node_automation(state)
            return state.get("final_output", "")
        elif intent == "code":
            state = self._node_code(state)
            return state.get("final_output", "")
        elif intent == "search":
            state = self._node_search(state)
        elif intent == "vision":
            state = self._node_vision(state)

        # Node 3: LLM Synthesizer
        state = self._node_llm(state)
        return state.get("final_output", "")

    def _node_router(self, state: AgentState) -> AgentState:
        """LangGraph Node: Classifies query intent."""
        cmd = state["user_input"].lower().strip()

        if any(w in cmd for w in ["open ", "kholo", "play ", "youtube", "notepad", "calc", "volume", "light", "pankha", "fan", "ac", "stop laalaa"]):
            state["intent"] = "automation"
        elif cmd.startswith("code ") or "write code" in cmd or "make code" in cmd:
            state["intent"] = "code"
        elif any(w in cmd for w in ["yolo", "camera scan", "kya dikh raha", "what do you see"]):
            state["intent"] = "vision"
        elif any(w in cmd for w in ["weather", "mausam", "who is", "what is", "where is", "search", "latest", "news", "temperature"]):
            state["intent"] = "search"
        else:
            state["intent"] = "chat"

        return state

    def _route_decision(self, state: AgentState) -> str:
        """LangGraph Conditional Edge Router."""
        return state.get("intent", "chat")

    def _node_search(self, state: AgentState) -> AgentState:
        """LangGraph Node: Fetches live web facts."""
        if self.search:
            try:
                facts = self.search.search_live(state["user_input"])
                state["web_facts"] = facts
            except Exception as e:
                print(f"[LangGraphEngine] Search node info: {e}")
        return state

    def _node_vision(self, state: AgentState) -> AgentState:
        """LangGraph Node: Scans scene via YOLO Vision."""
        if self.vision:
            try:
                ok, vision_res = self.vision.scan_and_detect()
                state["vision_facts"] = vision_res
            except Exception as e:
                print(f"[LangGraphEngine] Vision node info: {e}")
        return state

    def _node_automation(self, state: AgentState) -> AgentState:
        """LangGraph Node: Executes system automation / smart home actions."""
        if self.automation:
            try:
                ok, desc = self.automation.run(state["user_input"])
                state["action_result"] = desc
                state["final_output"] = desc
            except Exception as e:
                print(f"[LangGraphEngine] Automation node info: {e}")
        return state

    def _node_code(self, state: AgentState) -> AgentState:
        """LangGraph Node: Generates self-correcting Python code."""
        spec = state["user_input"].replace("write code for", "").replace("write code", "").replace("code ", "").strip()
        if not self.code_agent:
            from bishu.core.code_agent import CodeAgent
            self.code_agent = CodeAgent()

        try:
            res = self.code_agent.self_correcting_loop(spec)
            state["final_output"] = f"Code generated for '{spec}'.\n\n```python\n{res}\n```"
        except Exception as e:
            state["final_output"] = f"Code agent error: {e}"
        return state

    def _node_llm(self, state: AgentState) -> AgentState:
        """LangGraph Node: Synthesizes final response via MiniMax Cloud AI or Ollama."""
        if not self.ai:
            state["final_output"] = "Main bilkul khairiyat se hoon! Aap bataiye aapka kya haal hai?"
            return state

        cmd = state["user_input"]
        facts = state.get("web_facts") or state.get("vision_facts") or ""
        history_list = state.get("conversation_history", [])

        history_str = ""
        if history_list:
            lines = [f"{item.get('sender', 'User')}: {item.get('message', '')}" for item in history_list[-5:]]
            history_str = "Recent Conversation History:\n" + "\n".join(lines) + "\n\n"

        if facts:
            prompt = f"{history_str}Facts:\n{facts}\n\nUser: {cmd}\nYou are Laalaa, a warm, polite, intelligent AI companion (like J.A.R.V.I.S.). Respond politely as a close friend in 1 or 2 concise sentences matching the user's language (English, Hindi, Urdu).\nLaalaa:"
        else:
            prompt = f"{history_str}User: {cmd}\nYou are Laalaa, a warm, polite, intelligent AI companion (like J.A.R.V.I.S.). Respond politely as a close friend in 1 concise sentence matching the user's language (English, Hindi, Urdu).\nLaalaa:"

        reply = self.ai.generate(prompt)
        state["ai_reply"] = reply
        state["final_output"] = reply or "Main bilkul khairiyat se hoon! Aap ki kya khidmat karoon?"
        return state
