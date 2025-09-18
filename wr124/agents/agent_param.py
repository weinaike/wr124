import yaml
from pydantic import BaseModel, Field
from typing import List, Optional


class AgentParam(BaseModel):
    name: str = Field(..., description="The name of the agent")
    description: str = Field(..., description="A brief description of the agent")
    prompt: str = Field(..., description="The prompt to initiate the agent's behavior")
    model: Optional[str] = Field(None, description="The model used by the agent")
    color: Optional[str] = Field(None, description="The color associated with the agent")
    tools: List[str] = Field([], description="A list of tools available to the agent")
    max_tokens: Optional[int] = Field(None, description="The maximum number of tokens for the agent")
    max_compress_count: Optional[int] = Field(None, description="Maximum number of times to compress history")       
    max_tool_iterations: Optional[int] = Field(None, description="Maximum number of tool iterations")
    hook_agents: Optional[List[str]] = Field(None, description="List of file path for hook agent define to hook into main agent")
    task: Optional[str] = Field(None, description="The task description for the agent to perform, this is required for hook agents")


def parse_agent_markdown(file_path: str) -> AgentParam:
    """
    Parse an agent markdown file and convert it to a simplified dictionary.
    
    Args:
        file_path: Path to the markdown file
        
    Returns:
        Dictionary with fields: name, description, model, color, tools, prompt
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split content into frontmatter and body
    parts = content.split('---', 2)
    
    if len(parts) < 3:
        raise ValueError("Invalid markdown format: missing frontmatter")
    
    # Parse frontmatter (YAML)
    frontmatter_text = parts[1].strip()
    try:
        frontmatter = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML frontmatter: {e}")
    
    # Parse body content (everything after frontmatter becomes prompt)
    prompt = parts[2].strip()
    
    # Parse tools from frontmatter
    tools_str = frontmatter.get('tools', None)
    if isinstance(tools_str, str):
        # Split by comma and clean up whitespace
        tools = [tool.strip() for tool in tools_str.split(',') if tool.strip()]
    elif isinstance(tools_str, list):
        tools = tools_str
    else:
        tools = []

    hook_agents_str = frontmatter.get('hook_agents', None)
    if isinstance(hook_agents_str, str):
        hook_agents = [agent.strip() for agent in hook_agents_str.split(',') if agent.strip()]
    elif isinstance(hook_agents_str, list):
        hook_agents = hook_agents_str
    else:
        hook_agents = []

    # 处理名称，确保是有效的Python标识符
    name = frontmatter.get('name', '')
    # 将连字符替换为下划线，确保名称符合Python标识符规则
    name = name.replace('-', '_')

    result = AgentParam(
        name=name,
        description=frontmatter.get('description', ''),
        model=frontmatter.get('model', None),
        color=frontmatter.get('color', None),
        tools=tools,
        prompt=prompt,
        max_compress_count=frontmatter.get('max_compress_count', None),
        max_tokens=frontmatter.get('max_tokens', None),
        max_tool_iterations=frontmatter.get('max_tool_iterations', None),
        hook_agents=hook_agents if hook_agents else None,
        task=frontmatter.get('task', None),
    )

    return result
