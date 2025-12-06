# Graph-Based Agent Execution System

The SpoonOS graph-based execution system, inspired by LangGraph, provides a powerful framework for creating complex, stateful, and multi-step agent workflows. It allows developers to define agent behaviors as a graph of nodes and edges, enabling sophisticated logic, branching, and state management.

## Core Components

The system consists of two primary components: `StateGraph` and `GraphAgent`.

### 1. `StateGraph`

The [`StateGraph`](../spoon_ai/graph.py:26) is the blueprint for your workflow. It's a builder class used to define the structure of your agent's logic:

-   **Nodes**: Represent units of work. Each node is a Python function or coroutine that receives the current state and returns a dictionary of updates to be merged back into the state.
-   **Edges**: Define the flow of control between nodes. Edges can be unconditional (always transitioning from node A to node B) or conditional (routing to different nodes based on the current state).
-   **State**: A shared dictionary that is passed between nodes. It holds all the information the agent needs to perform its tasks, such as user input, intermediate results, and conversation history.

### 2. `GraphAgent`

The [`GraphAgent`](../spoon_ai/agents/graph_agent.py:19) is a specialized agent that executes a compiled `StateGraph`. It acts as a bridge between the graph workflow and the broader SpoonOS agent ecosystem. Its key responsibilities include:

-   Compiling the `StateGraph` into an executable format.
-   Preparing the initial state for a run, including user requests and memory.
-   Invoking the compiled graph and managing its execution cycle.
-   Extracting the final output from the terminal state.
-   Handling errors and managing execution history for debugging.

## Building a Workflow: A Step-by-Step Guide

Creating a graph-based workflow involves defining the state, creating node functions, and connecting them within a `StateGraph`.

### Step 1: Define Node Functions

Each node is a function that takes the current `state` dictionary and returns a dictionary of updates.

```python
# Node to greet the user
async def greet_user_node(state: dict) -> dict:
    print("Node: GREET_USER")
    user_name = state.get("user_name", "Guest")
    return {"greeting": f"Hello, {user_name}!"}

# Node to decide the next step
async def decide_next_step_node(state: dict) -> dict:
    print("Node: DECIDE_NEXT_STEP")
    if "end_conversation" in state.get("input", ""):
        return {"next_action": "END"}
    return {"next_action": "CONTINUE"}

# Node to say goodbye
async def say_goodbye_node(state: dict) -> dict:
    print("Node: SAY_GOODBYE")
    return {"output": "Goodbye!"}
```

### Step 2: Define Conditional Logic

Conditional edges use functions that inspect the state and return a string key, which maps to the next node to execute.

```python
# Condition function to route based on 'next_action' in the state
def route_logic(state: dict) -> str:
    print("Condition: Checking 'next_action'")
    return state.get("next_action", "END")
```

### Step 3: Construct the `StateGraph`

Instantiate `StateGraph` and add your nodes and edges.

```python
from spoon_ai.graph import StateGraph

# 1. Initialize the graph
workflow = StateGraph()

# 2. Add nodes
workflow.add_node("greet", greet_user_node)
workflow.add_node("decide", decide_next_step_node)
workflow.add_node("goodbye", say_goodbye_node)

# 3. Set the entry point for the graph
workflow.set_entry_point("greet")

# 4. Add edges
# Unconditional edge from 'greet' to 'decide'
workflow.add_edge("greet", "decide")

# Conditional edges from 'decide'
workflow.add_conditional_edges(
    "decide",
    route_logic,
    {
        "CONTINUE": "greet",  # If 'CONTINUE', loop back to 'greet'
        "END": "goodbye"      # If 'END', go to 'goodbye'
    }
)

# The 'goodbye' node has no outgoing edges, so the graph ends there.

# 5. Compile the graph
compiled_graph = workflow.compile()
```

## State Management

State is a fundamental concept in the graph execution system.

-   **Centralized State**: A single Python dictionary is passed to every node.
-   **Node Updates**: Each node returns a dictionary containing only the keys and values it wishes to add or update. The system automatically merges these changes into the main state.
-   **Immutability**: Nodes should not modify the state dictionary they receive directly. Instead, they should return a new dictionary with the desired changes.
-   **Initial State**: The `GraphAgent` automatically populates the initial state with useful information, including:
    -   `input` or `request`: The user's query.
    -   `messages`: The agent's memory.
    -   `agent_name`, `system_prompt`, etc.

## Complete Code Example

This example demonstrates a simple `GraphAgent` that greets a user and can decide to continue or end the conversation based on user input.

```python
import asyncio
from spoon_ai.graph import StateGraph
from spoon_ai.agents.graph_agent import GraphAgent

# --- Node and Condition Functions (from Step 1 & 2) ---

async def greet_user_node(state: dict) -> dict:
    print(f"Executing GREET node. Current greeting: {state.get('greeting')}")
    # This node will re-run if the graph loops
    return {"greeting": f"Hello again, {state.get('user_name', 'Guest')}!"}

async def decide_next_step_node(state: dict) -> dict:
    user_input = state.get("input", "").lower()
    print(f"Executing DECIDE node. User input: '{user_input}'")
    if "stop" in user_input:
        return {"next_action": "END"}
    return {"next_action": "CONTINUE"}

async def say_goodbye_node(state: dict) -> dict:
    print("Executing GOODBYE node.")
    return {"output": "Conversation ended. Goodbye!"}

def route_logic(state: dict) -> str:
    return state.get("next_action", "END")

# --- Graph and Agent Setup ---

def create_conversation_workflow():
    workflow = StateGraph()
    workflow.add_node("greet", greet_user_node)
    workflow.add_node("decide", decide_next_step_node)
    workflow.add_node("goodbye", say_goodbye_node)

    workflow.set_entry_point("decide")
    workflow.add_edge("greet", "decide")

    workflow.add_conditional_edges(
        "decide",
        route_logic,
        {"CONTINUE": "greet", "END": "goodbye"}
    )
    return workflow

async def main():
    # 1. Create the workflow
    conversation_graph = create_conversation_workflow()

    # 2. Create the GraphAgent
    agent = GraphAgent(
        name="conversation_agent",
        description="A simple conversational agent.",
        graph=conversation_graph,
        initial_state={"user_name": "Alice"} # Set initial state
    )

    # --- Run the Agent ---

    # First run
    print("\\n--- First Run: Continuing Conversation ---")
    result1 = await agent.run("Please continue.")
    print(f"\\nFinal Output: {result1}")
    print(f"Execution Path: {' -> '.join([step['node'] for step in agent.get_execution_history()])}")

    # Second run with exit condition
    print("\\n--- Second Run: Ending Conversation ---")
    agent.clear_state() # Clear history for clean demo
    result2 = await agent.run("Okay, please stop now.")
    print(f"\\nFinal Output: {result2}")
    print(f"Execution Path: {' -> '.join([step['node'] for step in agent.get_execution_history()])}")

if __name__ == "__main__":
    asyncio.run(main())
```

This example illustrates how to define a cyclical workflow that can be controlled by external input, showcasing the flexibility and power of the graph-based agent system.