#!/usr/bin/env python3
"""
进阶示例 01: 自定义节点开发
学习如何为ScholarFlow工作流添加自定义节点
"""

from typing import TypedDict
from langgraph.graph import StateGraph
import asyncio


# 示例 1: 定义自定义状态
class CustomWorkflowState(TypedDict, total=False):
    """扩展的工作流状态"""
    task_id: str
    status: str
    custom_field: str
    processing_count: int
    results: list


# 示例 2: 创建自定义节点
class CustomNode:
    """自定义节点基类"""

    def __init__(self, name: str):
        self.name = name

    async def execute(self, state: CustomWorkflowState) -> CustomWorkflowState:
        """执行节点逻辑"""
        print(f"\n🔧 执行节点: {self.name}")
        print(f"  任务ID: {state.get('task_id')}")
        print(f"  自定义字段: {state.get('custom_field')}")

        # 执行具体逻辑
        result = await self._process(state)

        # 返回状态更新
        return {
            "status": f"{self.name}_completed",
            "processing_count": state.get("processing_count", 0) + 1,
            "results": state.get("results", []) + [result]
        }

    async def _process(self, state: CustomWorkflowState) -> dict:
        """具体处理逻辑（子类实现）"""
        raise NotImplementedError("子类必须实现此方法")


# 示例 3: 具体自定义节点实现
class DataValidationNode(CustomNode):
    """数据验证节点"""

    def __init__(self):
        super().__init__("data_validation")

    async def _process(self, state: CustomWorkflowState) -> dict:
        """验证数据"""
        await asyncio.sleep(0.5)  # 模拟处理时间

        # 验证逻辑
        custom_field = state.get("custom_field", "")

        if not custom_field:
            raise ValueError("自定义字段不能为空")

        # 检查字段格式
        if len(custom_field) < 3:
            raise ValueError("自定义字段长度至少3个字符")

        return {
            "node": self.name,
            "validated": True,
            "field_length": len(custom_field),
            "timestamp": asyncio.get_event_loop().time()
        }


class DataTransformationNode(CustomNode):
    """数据转换节点"""

    def __init__(self):
        super().__init__("data_transformation")

    async def _process(self, state: CustomWorkflowState) -> dict:
        """转换数据"""
        await asyncio.sleep(0.3)

        custom_field = state.get("custom_field", "")
        processing_count = state.get("processing_count", 0)

        # 转换逻辑：添加处理标记
        transformed_field = f"[Processed-{processing_count}] {custom_field}"

        return {
            "node": self.name,
            "transformed": True,
            "original": custom_field,
            "transformed_field": transformed_field,
            "timestamp": asyncio.get_event_loop().time()
        }


class DataEnrichmentNode(CustomNode):
    """数据丰富节点"""

    def __init__(self):
        super().__init__("data_enrichment")

    async def _process(self, state: CustomWorkflowState) -> dict:
        """丰富数据"""
        await asyncio.sleep(0.4)

        # 模拟外部API调用
        enriched_data = {
            "node": self.name,
            "enriched": True,
            "metadata": {
                "source": "external_api",
                "confidence": 0.95,
                "tags": ["important", "verified"]
            },
            "timestamp": asyncio.get_event_loop().time()
        }

        return enriched_data


# 示例 4: 创建自定义工作流
class CustomWorkflow:
    """自定义工作流"""

    def __init__(self):
        self.nodes = {
            "data_validation": DataValidationNode(),
            "data_transformation": DataTransformationNode(),
            "data_enrichment": DataEnrichmentNode(),
        }

    def create_graph(self) -> StateGraph:
        """创建工作流图"""
        workflow = StateGraph(CustomWorkflowState)

        # 添加节点_node("data
        workflow.add_validation", self._node_wrapper("data_validation"))
        workflow.add_node(" self._node_wrapperdata_transformation",("data_transformation"))
        workflow.add_node("data_enrichment", self._node_wrapper("data_enrichment"))

        # 添加边
        workflow.add_edge("data_validation", "data_transformation")
        workflow.add_edge("data_transformation", "data_enrichment")

        # 设置入口点
        workflow.set_entry_point("data_validation")
        workflow.set_finish_point("data_enrichment")

        return workflow

    def _node_wrapper(self, node_name: str):
        """节点包装器"""
        async def wrapper(state: CustomWorkflowState) -> CustomWorkflowState:
            node = self.nodes[node_name]
            return await node.execute(state)

        return wrapper


# 示例 5: 条件路由节点
class ConditionalRouterNode(CustomNode):
    """条件路由节点"""

    def __init__(self):
        super().__init__("conditional_router")

    async def _process(self, state: CustomWorkflowState) -> dict:
        """条件路由"""
        await asyncio.sleep(0.2)

        processing_count = state.get("processing_count", 0)

        # 根据处理次数决定路由
        if processing_count < 3:
            route = "repeat_transformation"
        else:
            route = "proceed_to_enrichment"

        return {
            "node": self.name,
            "route": route,
            "processing_count": processing_count,
            "timestamp": asyncio.get_event_loop().time()
        }


def create_conditional_graph() -> StateGraph:
    """创建带条件路由的工作流"""
    workflow = StateGraph(CustomWorkflowState)

    # 添加节点
    workflow.add_node("validation", DataValidationNode().execute)
    workflow.add_node("transformation", DataTransformationNode().execute)
    workflow.add_node("router", ConditionalRouterNode().execute)
    workflow.add_node("enrichment", DataEnrichmentNode().execute)

    # 添加边
    workflow.add_edge("validation", "transformation")
    workflow.add_edge("transformation", "router")

    # 条件边
    workflow.add_conditional_edges(
        "router",
        route_after_processing,
        {
            "repeat_transformation": "transformation",
            "proceed_to_enrichment": "enrichment"
        }
    )

    workflow.set_entry_point("validation")
    workflow.set_finish_point("enrichment")

    return workflow


def route_after_processing(state: CustomWorkflowState) -> str:
    """路由决策函数"""
    results = state.get("results", [])
    if not results:
        return "proceed_to_enrichment"

    last_result = results[-1]
    route = last_result.get("route", "proceed_to_enrichment")

    print(f"  🧭 路由决策: {route}")
    return route


# 示例 6: 节点错误处理
class RobustNode(CustomNode):
    """带错误处理的鲁棒节点"""

    def __init__(self, name: str, max_retries: int = 3):
        super().__init__(name)
        self.max_retries = max_retries

    async def execute(self, state: CustomWorkflowState) -> CustomWorkflowState:
        """带重试的执行"""
        retry_count = 0

        while retry_count <= self.max_retries:
            try:
                print(f"\n🔧 执行节点: {self.name} (尝试 {retry_count + 1}/{self.max_retries + 1})")

                result = await self._process(state)

                # 成功，更新状态
                return {
                    "status": f"{self.name}_completed",
                    "results": state.get("results", []) + [result],
                    "error_message": None
                }

            except Exception as e:
                retry_count += 1
                error_msg = str(e)

                print(f"  ❌ 执行失败: {error_msg}")

                if retry_count > self.max_retries:
                    # 超过最大重试次数
                    return {
                        "status": f"{self.name}_failed",
                        "error_message": error_msg,
                        "retry_count": retry_count
                    }

                # 等待后重试
                await asyncio.sleep(0.5 * retry_count)  # 指数退避

        return state


# 示例 7: 异步批量处理节点
class BatchProcessingNode(CustomNode):
    """批量处理节点"""

    def __init__(self, batch_size: int = 3):
        super().__init__("batch_processing")
        self.batch_size = batch_size

    async def _process(self, state: CustomWorkflowState) -> dict:
        """批量处理"""
        items = state.get("custom_field", "").split(",")

        print(f"  📦 批量处理 {len(items)} 个项目，每批 {self.batch_size}")

        batches = [
            items[i:i + self.batch_size]
            for i in range(0, len(items), self.batch_size)
        ]

        results = []

        for batch_num, batch in enumerate(batches, 1):
            print(f"    处理批次 {batch_num}/{len(batches)}: {batch}")

            # 模拟批处理
            await asyncio.sleep(0.2)

            batch_result = {
                "batch_number": batch_num,
                "items": batch,
                "processed_at": asyncio.get_event_loop().time()
            }
            results.append(batch_result)

        return {
            "node": self.name,
            "total_batches": len(batches),
            "batch_results": results,
            "timestamp": asyncio.get_event_loop().time()
        }


# 示例 8: 执行自定义工作流
async def run_custom_workflow():
    """运行自定义工作流示例"""
    print("=" * 60)
    print("🔧 自定义节点工作流示例")
    print("=" * 60)

    # 示例 1: 基础自定义工作流
    print("\n" + "=" * 60)
    print("📋 示例 1: 基础自定义工作流")
    print("=" * 60)

    workflow = CustomWorkflow()
    graph = workflow.create_graph()
    compiled = graph.compile()

    initial_state = CustomWorkflowState(
        task_id="custom-001",
        status="pending",
        custom_field="test data",
        processing_count=0,
        results=[]
    )

    print(f"\n🚀 启动工作流: {initial_state['task_id']}")
    final_state = await compiled.ainvoke(initial_state)

    print(f"\n✅ 工作流完成:")
    print(f"  最终状态: {final_state['status']}")
    print(f"  处理次数: {final_state['processing_count']}")
    print(f"  结果数量: {len(final_state['results'])}")

    # 示例 2: 条件路由工作流
    print("\n" + "=" * 60)
    print("📋 示例 2: 条件路由工作流")
    print("=" * 60)

    conditional_graph = create_conditional_graph()
    compiled_conditional = conditional_graph.compile()

    initial_state2 = CustomWorkflowState(
        task_id="conditional-001",
        status="pending",
        custom_field="conditional test",
        processing_count=0,
        results=[]
    )

    print(f"\n🚀 启动条件路由工作流")
    final_state2 = await compiled_conditional.ainvoke(initial_state2)

    print(f"\n✅ 条件路由完成:")
    print(f"  最终状态: {final_state2['status']}")
    print(f"  处理次数: {final_state2['processing_count']}")

    # 示例 3: 鲁棒节点
    print("\n" + "=" * 60)
    print("📋 示例 3: 鲁棒节点（错误处理）")
    print("=" * 60)

    robust_node = RobustNode("robust_validation", max_retries=2)

    initial_state3 = CustomWorkflowState(
        task_id="robust-001",
        status="pending",
        custom_field="",  # 空字段会触发验证错误
        results=[]
    )

    print(f"\n🚀 测试错误处理")
    try:
        final_state3 = await robust_node.execute(initial_state3)
        print(f"\n✅ 鲁棒节点执行完成:")
        print(f"  状态: {final_state3['status']}")
        if final_state3.get('error_message'):
            print(f"  错误: {final_state3['error_message']}")
    except Exception as e:
        print(f"\n❌ 未处理的异常: {e}")

    # 示例 4: 批量处理
    print("\n" + "=" * 60)
    print("📋 示例 4: 批量处理节点")
    print("=" * 60)

    batch_node = BatchProcessingNode(batch_size=2)

    initial_state4 = CustomWorkflowState(
        task_id="batch-001",
        status="pending",
        custom_field="item1,item2,item3,item4,item5,item6,item7",
        results=[]
    )

    print(f"\n🚀 测试批量处理")
    final_state4 = await batch_node.execute(initial_state4)

    print(f"\n✅ 批量处理完成:")
    batch_result = final_state4['results'][-1]
    print(f"  总批次数: {batch_result['total_batches']}")
    print(f"  批次详情:")
    for batch in batch_result['batch_results']:
        print(f"    批次 {batch['batch_number']}: {batch['items']}")

    print("\n" + "=" * 60)
    print("✨ 自定义节点示例完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_custom_workflow())


"""
💡 学习要点:

1. 自定义节点基类
   - 统一的节点接口
   - 异步执行支持
   - 状态更新模式

2. 具体节点实现
   - 数据验证节点
   - 数据转换节点
   - 数据丰富节点

3. 条件路由
   - 动态路由决策
   - 循环处理
   - 分支控制

4. 错误处理
   - 重试机制
   - 指数退避
   - 优雅失败

5. 批量处理
   - 分批处理大量数据
   - 并发控制
   - 进度跟踪

📝 扩展练习:

1. 添加更多自定义节点类型
2. 实现并行处理节点
3. 添加节点间数据传递
4. 实现动态节点注册
5. 添加节点监控和指标

🔗 相关文档:

- LangGraph 节点: https://langchain-ai.github.io/langgraph/how-to_define-state/
- 自定义工作流: https://langchain-ai.github.io/langgraph/how-to_define-workflow/
"""
