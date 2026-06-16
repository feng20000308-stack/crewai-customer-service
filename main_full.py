import os
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import SerperDevTool, FileWriterTool, DirectoryReadTool

# 千问 API 配置
os.environ["DASHSCOPE_API_KEY"] = "sk-c0ea6827961b4b17b80dd8025785ea1c"
os.environ["DASHSCOPE_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# Serper 搜索 API（Google 搜索工具，免费额度：https://serper.dev）
# os.environ["SERPER_API_KEY"] = "your-serper-key"

llm = LLM(model="dashscope/qwen-plus")

# ========== 工具 ==========
# search_tool = SerperDevTool()       # 联网搜索
file_writer = FileWriterTool()        # 写文件
dir_reader = DirectoryReadTool()      # 读目录

# ========== Agent 1: 产品经理 ==========
pm = Agent(
    role="产品经理",
    goal="分析用户需求，输出清晰的产品需求文档(PRD)",
    backstory=(
        "你是一位有10年经验的互联网产品经理，擅长从模糊的需求中提炼出"
        "明确的功能点、用户故事和验收标准。你注重用户体验，善于权衡取舍。"
    ),
    verbose=True,
    allow_delegation=True,             # 允许把任务转给其他 Agent
    # memory=True,                     # 开启短期记忆（记住对话上下文）
    # inject_date=True,                # 自动注入当前日期
    llm=llm,
    tools=[dir_reader],                # 可以读取目录了解项目结构
)

# ========== Agent 2: 开发工程师 ==========
developer = Agent(
    role="高级Python开发工程师",
    goal="根据PRD编写高质量、可运行的Python代码",
    backstory=(
        "你是一位全栈Python工程师，精通FastAPI、数据处理、自动化脚本。"
        "你写的代码简洁、有类型注解、有错误处理，且附带必要的注释。"
    ),
    verbose=True,
    allow_delegation=False,
    llm=llm,
    tools=[file_writer, dir_reader],   # 可以写文件、读目录
)

# ========== Agent 3: 代码审查员 ==========
reviewer = Agent(
    role="代码审查专家",
    goal="审查代码质量，找出bug和改进点，确保代码达到生产标准",
    backstory=(
        "你是一位严格的代码审查员，关注代码风格、安全性、性能和可维护性。"
        "你会给出具体的修改建议，而不仅仅是指出问题。"
    ),
    verbose=True,
    allow_delegation=True,             # 可以把修改任务转回给开发
    llm=llm,
    tools=[dir_reader],
)

# ========== Task 1: 需求分析 ==========
prd_task = Task(
    description=(
        "针对以下需求进行分析，输出一份简洁的PRD：\n"
        "【需求】{requirement}\n\n"
        "PRD需要包含：\n"
        "1. 一句话描述产品目标\n"
        "2. 核心功能列表（3-5个）\n"
        "3. 每个功能的验收标准\n"
        "4. 技术建议（用什么框架/库）"
    ),
    expected_output="一份结构化的PRD文档，包含目标、功能列表、验收标准和技术建议",
    agent=pm,
)

# ========== Task 2: 编码实现 ==========
coding_task = Task(
    description=(
        "根据产品经理的PRD，编写完整的Python代码实现。\n"
        "要求：\n"
        "1. 代码可以直接运行\n"
        "2. 包含类型注解\n"
        "3. 有基本的错误处理\n"
        "4. 将代码写入文件 output/solution.py\n"
        "5. 代码顶部用注释说明如何运行"
    ),
    expected_output="完整的Python代码文件，已写入 output/solution.py",
    agent=developer,
    context=[prd_task],                # 依赖 PRD 的输出
)

# ========== Task 3: 代码审查 ==========
review_task = Task(
    description=(
        "审查开发工程师提交的代码，输出审查报告。\n"
        "审查维度：\n"
        "1. 代码正确性 - 是否满足PRD的验收标准\n"
        "2. 代码质量 - 风格、命名、结构\n"
        "3. 安全性 - 是否有注入、越权等风险\n"
        "4. 性能 - 是否有明显的性能问题\n"
        "5. 改进建议 - 具体的修改建议（附代码片段）\n\n"
        "如果发现严重问题，将修改任务委派给开发工程师。"
    ),
    expected_output="代码审查报告，包含评分、问题列表和改进建议",
    agent=reviewer,
    context=[coding_task],             # 依赖代码的输出
)

# ========== 组建 Crew ==========
crew = Crew(
    agents=[pm, developer, reviewer],
    tasks=[prd_task, coding_task, review_task],
    process=Process.sequential,        # 顺序执行：需求 → 编码 → 审查
    # process=Process.hierarchical,    # 层级模式：自动分配manager agent
    verbose=True,
    # memory=True,                     # 开启 crew 级别的记忆
    # embedder={                       # 自定义嵌入模型（用于记忆）
    #     "provider": "openai",
    #     "config": {"api_key": "...", "model": "text-embedding-3-small"}
    # },
    # planning=True,                   # 自动规划任务执行顺序
    # planning_llm=llm,
)

if __name__ == "__main__":
    requirement = "写一个命令行工具，能统计指定目录下所有Python文件的代码行数、注释行数和空行数，并输出统计表格"

    print(f"[Crew] 开始执行任务\n")
    result = crew.kickoff(inputs={"requirement": requirement})

    print("\n" + "=" * 60)
    print("[Crew] 最终输出：")
    print("=" * 60)
    print(result)
