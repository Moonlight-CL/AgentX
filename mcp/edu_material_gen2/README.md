# Educational Material Generation MCP Server

这是一个基于MCP (Model Context Protocol) 的教育教材生成服务器，提供两个主要功能：

1. **生成教育教材大纲prompt** - 根据学科主题和目标受众生成用于创建课程大纲的prompt
2. **生成详细教材内容prompt** - 根据章节信息生成用于创建详细教学材料的prompt

## 功能特性

### 1. 教材大纲prompt生成 (`generate_educational_outline`)
- 根据学科主题、目标受众、时长和难度生成大纲创建prompt
- 生成的prompt指导AI创建包含8-12个章节的详细大纲
- 每个章节包含标题、描述、学习目标、预计时长和难度等级

### 2. 详细教材prompt生成 (`generate_detailed_material`)
- 根据章节信息生成详细教材内容创建prompt
- 生成的prompt指导AI创建包含教学内容、实例案例、练习题、关键知识点和参考资料的完整教材

## 安装和运行

### 环境要求
- Python 3.11+

### 环境变量配置
在使用前，需要配置以下环境变量（在.env文件中）：

```bash
# Aurora PostgreSQL数据库连接配置
AURORA_HOST=your-aurora-host
AURORA_PORT=5432
AURORA_DATABASE=your-database
AURORA_USERNAME=your-username
AURORA_PASSWORD=your-password

# AWS配置
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_SESSION_TOKEN=your-session-token  # 可选，用于临时凭证
```

### 安装依赖
```bash
cd agentx-project/AgentX/mcp/edu_material_gen2
uv sync
```



### 运行服务器
```bash
# STDIO模式（默认）
uv run edu-material-server

# HTTP模式
uv run edu-material-server --transport http --port 8787
```

## 使用示例

### 1. 生成教材大纲
```json
{
  "tool": "generate_educational_outline",
  "arguments": {
    "subject": "Python编程基础",
    "target_audience": "编程初学者",
    "duration": "6周",
    "difficulty": "初级",
    "output_format": "json"
  }
}
```

### 2. 生成详细教材内容prompt
```json
{
  "tool": "generate_detailed_material",
  "arguments": {
    "subject": "Python编程基础",
    "target_audience": "编程初学者",
    "chapter_title": "Python基础概念",
    "chapter_description": "介绍Python的基本概念和语法",
    "learning_objectives": ["理解Python的基本语法", "掌握变量和数据类型", "学会基本的输入输出操作"],
    "estimated_duration": "1周",
    "difficulty_level": "初级"
  }
}
```

## 输出格式

工具返回的是用于生成教材的prompt文本，可以直接用于AI模型生成相应的教育内容。

### 大纲生成prompt示例
工具会生成类似以下的prompt：
```
请为以下教育课程生成详细的教材大纲：

学科主题: Python编程基础
目标受众: 编程初学者
总时长: 6周
难度等级: 初级

请生成一个包含8-12个章节的详细大纲，每个章节包括：
1. 章节标题
2. 章节描述
3. 预计学习时长
4. 难度等级
5. 学习目标（3-5个）

请以JSON格式返回，结构如下：
{
    "subject": "学科主题",
    "target_audience": "目标受众",
    "total_duration": "总时长",
    "outline_items": [...]
}
```

## 技术架构

- **框架**: 基于aws-db的MCP服务器框架
- **Prompt生成**: 生成结构化的AI prompt用于教材创建
- **错误处理**: 完善的错误处理和日志记录
- **轻量级**: 无需外部AI API，仅生成prompt文本

## 日志

服务器运行时会生成日志文件 `edu_material_gen_mcp_log.log`，记录所有操作和错误信息。

## 注意事项

1. 本工具仅生成prompt文本，不直接调用AI模型
2. 生成的prompt可以用于任何支持中文的AI模型
3. 支持中文内容生成，适合中文教育场景
4. 可以根据需要自定义prompt模板