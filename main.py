import os
from crewai import Agent, Task, Crew, Process, LLM

# 千问 API 配置（国内站）
os.environ["DASHSCOPE_API_KEY"] = "sk-c0ea6827961b4b17b80dd8025785ea1c"
os.environ["DASHSCOPE_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# 用 dashscope provider 创建 LLM
llm = LLM(model="dashscope/qwen-plus")

# ========== 定义 Agent ==========

researcher = Agent(
    role="资深研究分析师",
    goal="对给定主题进行深入调研，收集关键信息和数据",
    backstory="你是一位经验丰富的研究分析师，擅长从多个角度分析问题，"
              "提炼出最有价值的信息。你的分析总是条理清晰、重点突出。",
    verbose=True,
    allow_delegation=False,
    llm=llm,
)

writer = Agent(
    role="专业内容撰写人",
    goal="将研究成果转化为通俗易懂、结构清晰的中文文章",
    backstory="你是一位资深的内容创作者，擅长将复杂的技术或研究内容"
              "转化为普通人也能理解的文章，文风简洁有力。",
    verbose=True,
    allow_delegation=False,
    llm=llm,
)

# ========== 定义 Task ==========

research_task = Task(
    description=(
        "请对以下主题进行深入调研：\n"
        "【主题】{topic}\n\n"
        "要求：\n"
        "1. 梳理该主题的核心概念和背景\n"
        "2. 列出 3-5 个关键要点，每个要点附带简要说明\n"
        "3. 总结当前趋势或最新发展\n"
        "4. 输出结构化的研究报告"
    ),
    expected_output="一份结构化的中文研究报告，包含背景、关键要点和趋势总结",
    agent=researcher,
)

writing_task = Task(
    description=(
        "基于研究分析师提供的报告，撰写一篇面向大众的科普文章。\n"
        "要求：\n"
        "1. 标题吸引人\n"
        "2. 内容通俗易懂，避免过多术语\n"
        "3. 字数控制在 500-800 字\n"
        "4. 结构：引言 → 核心内容 → 总结展望"
    ),
    expected_output="一篇 500-800 字的中文科普文章，结构清晰、语言流畅",
    agent=writer,
    context=[research_task],  # 依赖研究任务的输出
)

# ========== 组建 Crew 并执行 ==========

crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, writing_task],
    process=Process.sequential,  # 按顺序执行：先研究，再写作
    verbose=True,
)

if __name__ == "__main__":
    # 修改这里可以测试不同主题
    topic = "大语言模型 Agent 的发展趋势"

    print(f"[Crew] 开始执行任务，主题：{topic}\n")
    result = crew.kickoff(inputs={"topic": topic})

    print("\n" + "=" * 60)
    print("[Crew] 最终输出：")
    print("=" * 60)
    print(result)
