import os
from crewai import Agent, Task, Crew, Process, LLM

# 千问 API 配置
os.environ["DASHSCOPE_API_KEY"] = "sk-c0ea6827961b4b17b80dd8025785ea1c"
os.environ["DASHSCOPE_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"

llm = LLM(model="dashscope/qwen-plus")

# ==================== Agent ====================

assistant = Agent(
    role="智能助手",
    goal="记住用户说过的信息，并在后续对话中利用这些记忆提供个性化回答",
    backstory=(
        "你是一个有记忆力的AI助手。你会记住用户告诉你的每一条信息，"
        "包括他们的偏好、习惯、工作内容等，并在后续对话中主动运用这些记忆。"
        "如果用户提到的信息和之前矛盾，你会指出并确认。"
    ),
    verbose=True,
    allow_delegation=False,
    llm=llm,
)

# ==================== 第一轮对话 ====================

task_round1 = Task(
    description=(
        "用户说：我叫张三，在杭州阿里云工作，做后端开发，喜欢用Python和Go。"
        "我最近在研究微服务架构，下周要给团队做一个技术分享。\n\n"
        "请：\n"
        "1. 确认你记住了哪些信息\n"
        "2. 针对他的技术分享主题，给出3个建议"
    ),
    expected_output="确认已记住的用户信息列表，以及针对技术分享的3个建议",
    agent=assistant,
)

# ==================== 第二轮对话（依赖第一轮的记忆）====================

task_round2 = Task(
    description=(
        "用户说：帮我整理一下我之前提到的技术分享的要点，"
        "另外我今天加班到很晚，帮我推荐个夜宵。\n\n"
        "注意：你需要回忆之前用户告诉过你的所有信息，"
        "包括他的名字、工作、技术栈、正在做的事情等，"
        "并在回答中体现你记住了这些。"
    ),
    expected_output="基于记忆的个性化回答，包含技术分享要点整理和夜宵推荐",
    agent=assistant,
    context=[task_round1],
)

# ==================== 第三轮对话（测试记忆一致性）====================

task_round3 = Task(
    description=(
        "用户说：对了我之前说错了，我不是在阿里云，是在网易。"
        "其他信息都是对的。\n\n"
        "请：\n"
        "1. 确认你更新了哪条记忆\n"
        "2. 用更新后的信息，给我一个完整的自我介绍（以我的口吻）"
    ),
    expected_output="确认记忆更新内容，以及基于最新信息的用户自我介绍",
    agent=assistant,
    context=[task_round1, task_round2],
)

# ==================== Crew（开启记忆）====================

crew = Crew(
    agents=[assistant],
    tasks=[task_round1, task_round2, task_round3],
    process=Process.sequential,
    verbose=True,
    # ===== 记忆配置 =====
    memory=True,                        # 开启 crew 级别记忆
    # 短期记忆：记住当前 crew 执行过程中的上下文（自动）
    # 长期记忆：跨多次 crew 执行的记忆（需要 embedder）
    # 实体记忆：自动提取和追踪实体信息（如人名、地点）
)

if __name__ == "__main__":
    print("[Crew] 记忆测试开始\n")
    result = crew.kickoff()

    print("\n" + "=" * 60)
    print("[Crew] 最终输出：")
    print("=" * 60)
    print(result)
