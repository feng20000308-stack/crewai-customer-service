import os
import json
from pathlib import Path
from datetime import datetime
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

# 千问 API 配置
os.environ["DASHSCOPE_API_KEY"] = "sk-c0ea6827961b4b17b80dd8025785ea1c"
os.environ["DASHSCOPE_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"

llm = LLM(model="dashscope/qwen-plus")

# ==================== 自定义工具 ====================

# 工具1：读取文件
class ReadFileInput(BaseModel):
    filepath: str = Field(description="要读取的文件路径")

class ReadFileTool(BaseTool):
    name: str = "read_file"
    description: str = "读取指定路径的文件内容，返回文本"
    args_schema: type[BaseModel] = ReadFileInput

    def _run(self, filepath: str) -> str:
        path = Path(filepath)
        if not path.exists():
            return f"错误：文件不存在 - {filepath}"
        try:
            return path.read_text(encoding="utf-8")
        except Exception as e:
            return f"读取失败：{e}"


# 工具2：写入文件
class WriteFileInput(BaseModel):
    filepath: str = Field(description="要写入的文件路径")
    content: str = Field(description="要写入的内容")

class WriteFileTool(BaseTool):
    name: str = "write_file"
    description: str = "将内容写入指定路径的文件"
    args_schema: type[BaseModel] = WriteFileInput

    def _run(self, filepath: str, content: str) -> str:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"成功写入 {filepath}（{len(content)} 字符）"


# 工具3：列出目录
class ListDirInput(BaseModel):
    dirpath: str = Field(description="要列出内容的目录路径")

class ListDirTool(BaseTool):
    name: str = "list_directory"
    description: str = "列出指定目录下的所有文件和子目录"
    args_schema: type[BaseModel] = ListDirInput

    def _run(self, dirpath: str) -> str:
        path = Path(dirpath)
        if not path.exists():
            return f"错误：目录不存在 - {dirpath}"
        items = []
        for item in sorted(path.iterdir()):
            prefix = "[DIR] " if item.is_dir() else "[FILE]"
            items.append(f"{prefix} {item.name}")
        return "\n".join(items) if items else "空目录"


# 工具4：获取当前时间
class DummyInput(BaseModel):
    placeholder: str = Field(default="无", description="无需填写")

class GetCurrentTimeTool(BaseTool):
    name: str = "get_current_time"
    description: str = "获取当前日期和时间，无需输入参数"
    args_schema: type[BaseModel] = DummyInput

    def _run(self, placeholder: str = "无") -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# 工具5：文本统计
class TextStatsInput(BaseModel):
    text: str = Field(description="要统计的文本内容")

class TextStatsTool(BaseTool):
    name: str = "text_stats"
    description: str = "统计文本的字符数、单词数、行数等信息"
    args_schema: type[BaseModel] = TextStatsInput

    def _run(self, text: str) -> str:
        lines = text.split("\n")
        words = text.split()
        chars = len(text)
        chinese = sum(1 for c in text if "一" <= c <= "鿿")
        return f"字符总数: {chars}\n中文字符: {chinese}\n英文单词: {len(words)}\n行数: {len(lines)}"


# ==================== Agent ====================

analyst = Agent(
    role="数据分析师",
    goal="读取、分析文件内容，提取关键信息并生成结构化报告",
    backstory=(
        "你是一位细致的数据分析师，擅长从文本和代码中提取有价值的信息。"
        "你会先了解文件结构，再深入分析内容，最后给出清晰的结论。"
    ),
    verbose=True,
    allow_delegation=False,
    llm=llm,
    tools=[ReadFileTool(), ListDirTool(), TextStatsTool(), GetCurrentTimeTool()],
)

writer = Agent(
    role="技术文档撰写人",
    goal="根据分析结果撰写清晰的技术文档，并保存到文件",
    backstory=(
        "你是一位技术写作专家，能将复杂的技术分析转化为易于理解的文档。"
        "你的文档结构清晰、用词精准，并且总会保存到合适的文件中。"
    ),
    verbose=True,
    allow_delegation=False,
    llm=llm,
    tools=[WriteFileTool(), ReadFileTool(), GetCurrentTimeTool()],
)

# ==================== Task ====================

analysis_task = Task(
    description=(
        "请完成以下工作：\n"
        "1. 读取文件 {target_file} 的内容\n"
        "2. 统计该文件的基本信息（字符数、行数等）\n"
        "3. 分析代码结构：定义了哪些函数/类，各有什么作用\n"
        "4. 评估代码质量：命名规范、注释情况、潜在问题\n"
        "5. 记录分析时间\n\n"
        "输出一份结构化的分析报告。"
    ),
    expected_output="一份结构化的代码分析报告，包含文件统计、结构分析和质量评估",
    agent=analyst,
)

doc_task = Task(
    description=(
        "根据分析报告，撰写一份技术文档并保存到文件。\n"
        "要求：\n"
        "1. 文档包含：概述、详细分析、改进建议\n"
        "2. 将文档保存到 {output_file}\n"
        "3. 确认文件写入成功\n"
        "4. 记录文档生成时间"
    ),
    expected_output="确认文档已保存到指定路径，输出文件路径和文档摘要",
    agent=writer,
    context=[analysis_task],
)

# ==================== Crew ====================

crew = Crew(
    agents=[analyst, writer],
    tasks=[analysis_task, doc_task],
    process=Process.sequential,
    verbose=True,
)

if __name__ == "__main__":
    print("[Crew] 开始执行\n")
    result = crew.kickoff(inputs={
        "target_file": "D:/python/crewai/main.py",
        "output_file": "D:/python/crewai/output/code_review.md",
    })

    print("\n" + "=" * 60)
    print("[Crew] 最终输出：")
    print("=" * 60)
    print(result)
