# 🛠️ SpoonOS CLI Usage Guide

SCDF CLI is a powerful command-line tool that provides rich functionality, including interacting with AI agents, managing chat history, processing cryptocurrency transactions, and loading documents.

## 🚀 Start the CLI

Once the MCP server is running, launch the CLI:

```bash
python main.py
```

## 📋 Available Agents

The CLI includes these built-in agents:

| Agent | Aliases | Type | MCP Support | Description |
|-------|---------|------|-------------|-------------|
| `react` | `spoon_react` | SpoonReactAI | ❌ | Standard blockchain analysis agent |
| `spoon_react_mcp` | - | SpoonReactMCP | ✅ | MCP-enabled blockchain agent |

**Note**: Additional agents can be configured in `config.json` (see examples below).

### Loading Agents

```bash
# List all available agents
> list-agents

# Load built-in agent by name
> load-agent react
> load-agent spoon_react_mcp

# Load agent by alias
> load-agent spoon_react

# Check currently loaded agent
> list-agents
```

## Basic Commands

| Command             | Aliases           | Description                                                                                                               |
| ------------------- | ----------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `help`              | `h`, `?`          | Display help information                                                                                                  |
| `exit`              | `quit`, `q`       | Exit the CLI                                                                                                              |
| `system-info`       | `sysinfo`, `status`, `info` | Display comprehensive system information, environment status, and health checks                                    |
| `load-agent <n>` | `load`            | Load an agent with the specified name                                                                                     |
| `list-agents`       | `agents`          | List all available agents                                                                                                 |
| `config`            | `cfg`, `settings` | Configure settings (such as API keys)                                                                                     |
| `reload-config`     | `reload`          | Reload the current agent's configuration                                                                                  |
| `action <action>`   | `a`               | Perform a specific action using the current agent. For example, `action react` to start a step-by-step reasoning session. |

### Chat Management Commands

| Command          | Aliases | Description                         |
| ---------------- | ------- | ----------------------------------- |
| `new-chat`       | `new`   | Start a new chat (clear history)    |
| `list-chats`     | `chats` | List available chat history records |
| `load-chat <ID>` | -       | Load a specific chat history record |

### Cryptocurrency-Related Commands

| Command                                       | Aliases  | Description                            |
| --------------------------------------------- | -------- | -------------------------------------- |
| `transfer <address> <amount> <token>`         | `send`   | Transfer tokens to a specified address |
| `swap <source_token> <target_token> <amount>` | -        | Exchange tokens using an aggregator    |
| `token-info <address>`                        | `token`  | Get token information by address       |
| `token-by-symbol <symbol>`                    | `symbol` | Get token information by symbol        |

### Document Management Commands

| Command                      | Aliases | Description                                                      |
| ---------------------------- | ------- | ---------------------------------------------------------------- |
| `load-docs <directory_path>` | `docs`  | Load documents from the specified directory to the current agent |

### LLM Provider Management Commands

| Command                           | Aliases    | Description                                    |
| --------------------------------- | ---------- | ---------------------------------------------- |
| `list-providers`                  | `providers`| List all available LLM providers              |
| `set-provider <provider>`         | `provider` | Set the default LLM provider                  |
| `test-provider <provider>`        | `test`     | Test connectivity to a specific provider      |
| `provider-status`                 | `status`   | Show health status of all providers           |
| `provider-stats <provider>`       | `stats`    | Show performance statistics for a provider    |
| `config provider <name> <key> <value>` | -    | Configure provider-specific settings          |

## ⚙️ Configuration Management

### Environment Variables

Set required API keys before starting:

```bash
# Required for web search (Tavily MCP)
export TAVILY_API_KEY="your-tavily-api-key"

# Required for LLM functionality
export OPENAI_API_KEY="your-openai-api-key"

# Optional: Debug mode
export DEBUG=true
export LOG_LEVEL=debug
```

### Agent Configuration

Custom agents can be configured in `spoon-core/config.json`. The basic structure is:

```json
{
  "default_agent": "react",
  "agents": {
    "my_custom_agent": {
      "class": "SpoonReactAI",
      "aliases": ["my", "custom"],
      "description": "My custom agent",
      "config": {
        "max_steps": 10,
        "tool_choice": "auto"
      },
      "tools": [
        { "name": "crypto_tools", "type": "builtin", "enabled": true }
      ]
    }
  }
}
```

For MCP-enabled agents, each tool must be an object with `type: "mcp"` and an `mcp_server` section that specifies how to connect to the MCP server (stdio or URL). Example (DeepWiki via SSE):

```json
{
  "agents": {
    "deepwiki_agent": {
      "class": "SpoonReactMCP",
      "description": "DeepWiki agent for GitHub repository documentation",
      "aliases": ["deepwiki", "docs"],
      "tools": [
        {
          "name": "read_wiki_structure",
          "type": "mcp",
          "description": "Get documentation structure for GitHub repos",
          "mcp_server": {
            "url": "https://mcp.deepwiki.com/mcp",
            "transport": "http",
            "timeout": 30,
            "headers": {
              "User-Agent": "SpoonOS-MCP/1.0",
              "Accept": "application/json, text/event-stream"
            }
          }
        }
      ]
    }
  }
}
```

#### Example: Using DeepWiki Agent

After configuring the DeepWiki agent, you can use it to analyze GitHub repositories:

```bash
# Load the DeepWiki agent
> load-agent deepwiki_agent

# Ask about XSpoonAi/spoon-core repository
> Can you analyze the XSpoonAi/spoon-core repository and tell me what this project does?

# Ask about React repository
> What are the main documentation topics available for facebook/react?
```

### MCP Server Types

SpoonOS supports stdio and URL-based (SSE/WebSocket) MCP servers.

| Method | Use Case | Configuration Example |
|--------|----------|----------------------|
| `npx` | Node.js packages | `"command": "npx", "args": ["-y", "package-name"]` |
| `python` | Python scripts | `"command": "python", "args": ["server.py"]` |
| `uvx` | uvx-installed CLIs | `"command": "uvx", "args": ["package-or-entrypoint"]` |
| `http` | HTTP/HTTPS | `"url": "https://example.com/mcp", "transport": "http"` |
| `sse` | HTTP/HTTPS SSE | `"url": "https://example.com/mcp", "transport": "sse"` |

### Configuration Commands

```bash
# Reload configuration after changes
> reload-config

# Check current configuration
> config

# Update specific settings
> config API_KEY your-new-key

# LLM Provider Management
> list-providers                    # List available LLM providers
> set-provider openai              # Set default LLM provider
> test-provider anthropic          # Test provider connectivity
> provider-status                  # Show provider health status
> config provider openai model gpt-4.1-turbo  # Configure provider settings
```

### System Diagnostics

The `system-info` command provides comprehensive system diagnostics and health checks:

```bash
# Display full system information
> system-info

# Using aliases
> sysinfo
> status
> info
```

This command shows:
- **System Details**: Platform, Python version, architecture, timestamp
- **Environment Variables**: Status of all API keys and configuration (with security masking)
- **Configuration Status**: Validates config.json and detects placeholder values
- **Agent Status**: Current agent information, tools, and LLM provider
- **Health Checks**: Automated scoring with recommendations for improvements

**Example Output:**
```
🔍 SpoonAI System Information
═══════════════════════════════════════

📊 System Details:
  Platform: macOS 13.0
  Python Version: 3.11.0
  Architecture: arm64

🔑 Environment Variables:
  OpenAI API           ✓ Set - ********... (length: 64)
  Anthropic API        ✗ Not set
  Secret Key           ✓ Set - ********... (length: 32)

🏥 Health Check Summary:
  ✓ LLM API key configured
  ✓ Security key configured
  ✓ Configuration file present
  ✓ Agent is loaded and ready

  Overall Health: Excellent (4/4 checks passed)
```

## CLI Usage Examples

#### Configure Settings

1. View current configuration:

```
> config
Current configuration:
API_KEY: sk-***********
MODEL: gpt-4.1
...
```

2. Modify configuration:

```
> config API_KEY sk-your-new-api-key
API_KEY updated
```

#### LLM Provider Management

1. List available providers:

```
> list-providers
Available LLM providers:
✅ openai (gpt-4.1) - Healthy
✅ anthropic (claude-sonnet-4-20250514) - Healthy
❌ gemini (gemini-2.5-pro) - Unhealthy
Default provider: openai
```

2. Switch default provider:

```
> set-provider anthropic
Default LLM provider set to: anthropic
```

3. Test provider connectivity:

```
> test-provider openai
Testing OpenAI provider...
✅ Connection successful
Model: gpt-4.1
Response time: 1.2s
```

4. View provider statistics:

```
> provider-stats openai
OpenAI Provider Statistics:
Total requests: 1,247
Successful requests: 1,198 (96.1%)
Average response time: 2.3s
Rate limit hits: 12
Last error: 2 hours ago
```

5. Configure provider settings:

```
> config provider openai model gpt-4.1-turbo
OpenAI model updated to: gpt-4.1-turbo

> config provider anthropic temperature 0.7
Anthropic temperature updated to: 0.7

> config provider openai max_tokens 8192
OpenAI max_tokens updated to: 8192
```

#### Basic Interaction

1. Start a new chat:

```
> action chat
New chat session started
```

3. Directly input text to interact with the AI agent:

```
> Hello, please introduce yourself
[AI reply will be displayed here]
```

#### Cryptocurrency Operations

1. View token information:

```
> token-by-symbol SPO
Token information:
Name: SpoonOS not a meme
Symbol:SPO
Address: 0x...
Decimals: 18
...
```

2. Transfer operation:

```
> transfer 0x123... 0.1 SPO
Preparing to transfer 0.1 SPO to 0x123...
[Transfer details will be displayed here]
```

## 🔧 Troubleshooting

### Common Issues

| Issue | Symptoms | Solution |
|-------|----------|----------|
| **Agent not found** | `Agent 'name' not found` | Use `list-agents` to check available agents, verify spelling |
| **MCP connection failed** | `Failed to create transport` | Check API keys, verify MCP server is running |
| **Tool not available** | `Tool 'name' not found` | Check `tools` config, verify MCP server enabled |
| **Duplicate agents** | Same agent appears twice | Fixed in latest version, restart if needed |
| **API key missing** | Authentication errors | Set environment variables: `TAVILY_API_KEY`, `OPENAI_API_KEY` |

### Debug Mode

Enable detailed logging:

```bash
export DEBUG=true
export LOG_LEVEL=debug
python main.py
```

### Configuration Validation

1. **Check JSON syntax**: Use a JSON validator for `config.json`
2. **Verify required fields**: Ensure all required parameters are present
3. **Test MCP servers**: Verify external services are accessible
4. **Check environment variables**: Confirm all API keys are set

### LLM Provider Troubleshooting

| Issue | Command | Solution |
|-------|---------|----------|
| Provider not responding | `test-provider <name>` | Check API key and connectivity |
| High error rate | `provider-stats <name>` | Review error patterns and adjust config |
| Slow responses | `provider-stats <name>` | Check response times and consider alternatives |
| Authentication failed | `config provider <name> api_key <key>` | Update API key |
| Model not available | `list-providers` | Check available models and update config |

### Common CLI Troubleshooting Commands

```bash
# Diagnose provider issues
> provider-status                   # Overall health check
> test-provider openai             # Test specific provider
> provider-stats openai            # Detailed statistics
> show-logs llm                    # View LLM-related logs

# Configuration debugging
> config validate                  # Validate configuration
> config reset                     # Reset to defaults
> reload-config                    # Reload configuration

# Agent troubleshooting
> list-agents                      # Check available agents
> agent-status                     # Current agent status
> clear-cache                      # Clear agent cache
```

### Example: Custom Search Agent Configuration

Here's how to configure a custom search agent with MCP integration (stdio-based):

```json
{
  "default_agent": "my_search_agent",
  "agents": {
    "my_search_agent": {
      "class": "SpoonReactMCP",
      "aliases": ["search", "web"],
      "description": "Custom search agent with web capabilities",
      "tools": [
        {
          "name": "tavily_search",
          "type": "mcp",
          "mcp_server": {
            "command": "npx",
            "args": ["-y", "tavily-mcp"],
            "env": { "TAVILY_API_KEY": "your-key" }
          }
        },
        { "name": "crypto_tools", "type": "builtin" }
      ]
    }
  }
}
```

After adding this configuration, the agent will appear in `list-agents` and can be loaded with:
```bash
> load-agent my_search_agent
> load-agent search  # using alias
```

## ✅ Next Steps

To extend CLI usage:

- 🤖 [Explore agent capabilities](./agent.md)
- 🌐 [Use Web3 tools via MCP](./mcp_mode_usage.md)
