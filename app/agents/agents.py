"""
AI Agents - Specialized agents for different development tasks
"""
import os
import anthropic
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 2048

AGENT_SYSTEM_PROMPTS = {
    "general": """You are an AI Developer Project Manager assistant. You help developers understand their codebases, 
plan features, debug issues, and manage projects. Be concise, practical, and developer-friendly.
Always format code blocks with proper markdown. Use bullet points for lists.""",

    "planning": """You are a Planning Agent — an expert software project planner and technical lead.
Your job is to break down features into actionable tasks, estimate complexity, create sprint plans,
and organize development work. Output tasks in a clear, structured format.
When generating tasks, always include: title, description, complexity (1-10), priority (low/medium/high), 
and relevant tags. Format task lists as JSON when asked.""",

    "coding": """You are a Coding Agent — an expert software engineer and code reviewer.
Your job is to write clean code, review existing code, suggest refactors, and implement features.
Always follow best practices for the language/framework in use. Provide complete, working code examples.
Format all code in proper markdown code blocks with language identifiers.""",

    "debugging": """You are a Debugging Agent — an expert at analyzing errors, stack traces, and bugs.
Your job is to identify the root cause of issues, explain them clearly, and provide concrete fixes.
Structure your response as:
1. **Root Cause**: What is causing the error
2. **Explanation**: Why this happens
3. **Fix**: Exact code/steps to resolve it
4. **Prevention**: How to avoid this in the future
Always be specific and provide working solutions.""",

    "documentation": """You are a Documentation Agent — an expert technical writer and architect.
Your job is to generate clear documentation, architecture summaries, API docs, and README files.
Write documentation that is developer-friendly, accurate, and well-structured.
Use proper markdown formatting with headers, code blocks, and clear explanations.""",

    "repo_chat": """You are a Repository Assistant — an expert at understanding and explaining codebases.
You have access to repository context and can answer questions about the code structure, 
patterns, architecture, and implementation details. Be precise and reference specific files when relevant.
If you're not sure about something, say so rather than guessing.""",
}


class BaseAgent:
    def __init__(self, agent_type: str = "general"):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.agent_type = agent_type
        self.system_prompt = AGENT_SYSTEM_PROMPTS.get(agent_type, AGENT_SYSTEM_PROMPTS["general"])

    def _sanitize_input(self, text: str) -> str:
        """Basic input sanitization to prevent prompt injection."""
        # Remove common injection patterns
        dangerous = ["ignore previous instructions", "system:", "SYSTEM:", "Human:", "Assistant:"]
        for d in dangerous:
            text = text.replace(d, "[filtered]")
        return text[:10000]  # Limit input length

    def chat(self, messages: List[Dict], extra_context: str = "") -> str:
        """Send a chat message and get a response."""
        system = self.system_prompt
        if extra_context:
            system += f"\n\n=== CONTEXT ===\n{extra_context[:4000]}"
        try:
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=messages[-20:],  # Keep last 20 messages
            )
            return response.content[0].text
        except Exception as e:
            return f"Agent error: {str(e)}"

    def one_shot(self, prompt: str, context: str = "") -> str:
        """Single prompt, single response."""
        prompt = self._sanitize_input(prompt)
        return self.chat([{"role": "user", "content": prompt}], extra_context=context)


class PlanningAgent(BaseAgent):
    def __init__(self):
        super().__init__("planning")

    def generate_tasks(self, feature_description: str, project_context: str = "") -> str:
        prompt = f"""Generate a detailed task breakdown for this feature:

**Feature**: {feature_description}

Return a JSON array of tasks with this structure:
[
  {{
    "title": "Task title",
    "description": "Detailed description",
    "complexity": 5,
    "priority": "high",
    "tags": ["backend", "api"]
  }}
]

Generate 4-8 specific, actionable tasks. Return ONLY valid JSON, no other text."""
        return self.one_shot(prompt, context=project_context)

    def estimate_sprint(self, tasks: List[Dict]) -> str:
        task_list = "\n".join([f"- {t.get('title', 'Unknown')} (complexity: {t.get('complexity', 3)})"
                               for t in tasks])
        prompt = f"""Given these tasks, create a sprint plan with time estimates:

{task_list}

Provide:
1. Total story points
2. Recommended sprint duration
3. Task ordering and dependencies
4. Risk factors"""
        return self.one_shot(prompt)


class CodingAgent(BaseAgent):
    def __init__(self):
        super().__init__("coding")

    def review_code(self, code: str, language: str = "unknown") -> str:
        prompt = f"""Review this {language} code and provide:
1. Quality assessment (1-10)
2. Issues found
3. Security concerns
4. Improvement suggestions
5. Refactored version if needed

```{language}
{code[:3000]}
```"""
        return self.one_shot(prompt)

    def implement_feature(self, description: str, existing_code: str = "", language: str = "Python") -> str:
        context = f"Existing code:\n```{language}\n{existing_code[:2000]}\n```" if existing_code else ""
        prompt = f"""Implement this feature in {language}:

{description}

Provide complete, production-ready code with:
- Proper error handling
- Type hints (if applicable)
- Comments for complex logic
- Example usage"""
        return self.one_shot(prompt, context=context)


class DebuggingAgent(BaseAgent):
    def __init__(self):
        super().__init__("debugging")

    def analyze_error(self, error: str, code_context: str = "", project_context: str = "") -> Dict:
        context = project_context
        if code_context:
            context += f"\n\nCode context:\n```\n{code_context[:2000]}\n```"

        prompt = f"""Analyze this error and provide a complete solution:

```
{error[:3000]}
```

Structure your response with these exact headers:
## Root Cause
## Explanation  
## Fix
## Prevention"""
        response = self.one_shot(prompt, context=context)
        return {
            "analysis": response,
            "error_snippet": error[:200],
        }

    def find_risky_code(self, code: str, language: str = "unknown") -> str:
        prompt = f"""Analyze this {language} code for security risks, bugs, and dangerous patterns:

```{language}
{code[:3000]}
```

Identify:
1. Security vulnerabilities
2. Potential runtime errors
3. Memory/resource issues
4. Anti-patterns
5. Recommended fixes"""
        return self.one_shot(prompt)


class DocumentationAgent(BaseAgent):
    def __init__(self):
        super().__init__("documentation")

    def generate_readme(self, project_context: str) -> str:
        prompt = """Generate a comprehensive README.md for this project.

Include:
# Project Name
## Overview
## Features
## Tech Stack
## Installation
## Usage
## API Documentation (if applicable)
## Contributing
## License"""
        return self.one_shot(prompt, context=project_context)

    def summarize_architecture(self, project_context: str) -> str:
        prompt = """Generate a clear architecture summary of this project.

Include:
1. High-level overview
2. Component breakdown
3. Data flow
4. Key design decisions
5. Technology choices and rationale"""
        return self.one_shot(prompt, context=project_context)

    def document_function(self, code: str, language: str = "Python") -> str:
        prompt = f"""Generate complete documentation for this {language} code:

```{language}
{code[:2000]}
```

Include:
- Purpose and description
- Parameters and types
- Return values
- Examples
- Edge cases"""
        return self.one_shot(prompt)


class RepoChatAgent(BaseAgent):
    def __init__(self):
        super().__init__("repo_chat")

    def answer_question(self, question: str, repo_context: str, conversation_history: List[Dict] = None) -> str:
        question = self._sanitize_input(question)
        messages = conversation_history or []
        messages = messages[-10:]  # Last 10 turns
        messages.append({"role": "user", "content": question})
        return self.chat(messages, extra_context=repo_context)


# ─── Agent Orchestrator ────────────────────────────────────────────────────────

class AgentOrchestrator:
    """Routes tasks to the appropriate specialized agent."""

    def __init__(self):
        self._agents = {}

    def _get_agent(self, agent_type: str) -> BaseAgent:
        if agent_type not in self._agents:
            agent_map = {
                "planning": PlanningAgent,
                "coding": CodingAgent,
                "debugging": DebuggingAgent,
                "documentation": DocumentationAgent,
                "repo_chat": RepoChatAgent,
                "general": lambda: BaseAgent("general"),
            }
            cls = agent_map.get(agent_type, lambda: BaseAgent("general"))
            self._agents[agent_type] = cls()
        return self._agents[agent_type]

    def route(self, agent_type: str, task: str, context: str = "", **kwargs) -> str:
        """Route a task to the appropriate agent."""
        agent = self._get_agent(agent_type)
        return agent.one_shot(task, context=context)

    def generate_tasks(self, feature: str, context: str = "") -> str:
        agent = self._get_agent("planning")
        return agent.generate_tasks(feature, context)

    def analyze_error(self, error: str, code: str = "", context: str = "") -> Dict:
        agent = self._get_agent("debugging")
        return agent.analyze_error(error, code, context)

    def answer_repo_question(self, question: str, repo_context: str, history: List[Dict] = None) -> str:
        agent = self._get_agent("repo_chat")
        return agent.answer_question(question, repo_context, history)

    def summarize_architecture(self, context: str) -> str:
        agent = self._get_agent("documentation")
        return agent.summarize_architecture(context)

    def generate_readme(self, context: str) -> str:
        agent = self._get_agent("documentation")
        return agent.generate_readme(context)

    def review_code(self, code: str, language: str = "unknown") -> str:
        agent = self._get_agent("coding")
        return agent.review_code(code, language)

    def general_chat(self, messages: List[Dict], context: str = "") -> str:
        agent = self._get_agent("general")
        return agent.chat(messages, extra_context=context)
