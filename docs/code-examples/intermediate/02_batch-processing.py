#!/usr/bin/env python3
"""
进阶示例 02: 批量处理
学习如何实现高效的批量处理
"""

import asyncio
import time
from typing import List, Dict, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed


@dataclass
class BatchItem:
    """批量处理项"""
    id: str
    data: str
    priority: int = 0
    metadata: Dict[str, Any] = None


class BatchProcessor:
    """批量处理器"""

    def __init__(self, batch_size: int = 5, max_workers: int = 3):
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.results = []

    async def process_batch(self, items: List[BatchItem]) -> List[Dict]:
        """处理一批项目"""
        print(f"\n📦 开始处理 {len(items)} 个项目")

        # 创建任务
        tasks = [self._process_item(item) for item in items]

        # 并发执行（有限并发）
        semaphore = asyncio.Semaphore(self.max_workers)
        bounded_tasks = [self._bounded_process(item, semaphore) for item, item in zip(items, tasks)]

        results = await asyncio.gather(*bounded_tasks, return_exceptions=True)

        # 处理结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"  ❌ 项目 {items[i].id} 处理失败: {result}")
                processed_results.append({
                    "id": items[i].id,
                    "success": False,
                    "error": str(result)
                })
            else:
                processed_results.append(result)

        print(f"✅ 批次处理完成: {len(processed_results)}/{len(items)} 成功")
        return processed_results

    async def _bounded_process(self, item: BatchItem, semaphore: asyncio.Semaphore):
        """带并发限制的处理"""
        async with semaphore:
            return await self._process_item(item)

    async def _process_item(self, item: BatchItem) -> Dict:
        """处理单个项目"""
        print(f"  🔄 处理项目: {item.id}")
        start_time = time.time()

        # 模拟处理时间
        await asyncio.sleep(0.5)

        # 模拟可能的错误
        if "error" in item.data.lower():
            raise ValueError(f"模拟错误: {item.id}")

        result = {
            "id": item.id,
            "success": True,
            "data": item.data.upper(),
            "priority": item.priority,
            "processing_time": time.time() - start_time,
            "timestamp": time.time()
        }

        print(f"  ✅ 项目 {item.id} 处理完成 ({result['processing_time']:.2f}s)")
        return result

    async def process_all(self, all_items: List[BatchItem]) -> List[Dict]:
        """处理所有项目（分批）"""
        print(f"\n🚀 开始批量处理 {len(all_items)} 个项目")
        print(f"  批次大小: {self.batch_size}")
        print(f"  最大并发: {self.max_workers}")

        # 按优先级排序
        sorted_items = sorted(all_items, key=lambda x: x.priority, reverse=True)

        # 分批处理
        all_results = []
        for i in range(0, len(sorted_items), self.batch_size):
            batch = sorted_items[i:i + self.batch_size]
            print(f"\n{'=' * 60}")
            print(f"批次 {i // self.batch_size + 1}/{(len(sorted_items) + self.batch_size - 1) // self.batch_size}")
            print(f"{'=' * 60}")

            batch_results = await self.process_batch(batch)
            all_results.extend(batch_results)

            # 显示批次统计
            success_count = sum(1 for r in batch_results if r.get("success", False))
            avg_time = sum(r.get("processing_time", 0) for r in batch_results) / len(batch_results)
            print(f"  统计: {success_count}/{len(batch)} 成功, 平均耗时 {avg_time:.2f}s")

        print(f"\n🎉 全部处理完成!")
        print(f"  总计: {len(all_results)} 个项目")
        print(f"  成功: {sum(1 for r in all_results if r.get('success', False))}")
        print(f"  失败: {sum(1 for r in all_results if not r.get('success', False))}")

        return all_results


class AdvancedBatchProcessor:
    """高级批量处理器"""

    def __init__(self):
        self.processors = {
            "validation": self._validate,
            "transformation": self._transform,
            "enrichment": self._enrich,
        }

    async def process_with_pipeline(self, items: List[BatchItem]) -> List[Dict]:
        """使用管道处理"""
        print(f"\n🔄 管道处理 {len(items)} 个项目")

        # 阶段1: 验证
        print("\n阶段 1: 验证")
        validated_items = []
        for item in items:
            try:
                validated = await self._validate(item)
                if validated["valid"]:
                    validated_items.append(item)
                else:
                    print(f"  ⚠️  项目 {item.id} 验证失败: {validated['reason']}")
            except Exception as e:
                print(f"  ❌ 项目 {item.id} 验证异常: {e}")

        print(f"  验证通过: {len(validated_items)}/{len(items)}")

        # 阶段2: 转换
        print("\n阶段 2: 转换")
        transformed_items = []
        for item in validated_items:
            try:
                transformed = await self._transform(item)
                transformed_items.append(transformed)
            except Exception as e:
                print(f"  ❌ 项目 {item.id} 转换失败: {e}")

        print(f"  转换完成: {len(transformed_items)}")

        # 阶段3: 丰富
        print("\n阶段 3: 丰富")
        final_results = []
        for item in transformed_items:
            try:
                enriched = await self._enrich(item)
                final_results.append(enriched)
            except Exception as e:
                print(f"  ❌ 项目 {item.id} 丰富失败: {e}")

        print(f"  丰富完成: {len(final_results)}")
        return final_results

    async def _validate(self, item: BatchItem) -> Dict:
        """验证"""
        await asyncio.sleep(0.2)

        if not item.data.strip():
            return {"valid": False, "reason": "数据为空"}

        if len(item.data) < 3:
            return {"valid": False, "reason": "数据过短"}

        return {"valid": True}

    async def _transform(self, item: BatchItem) -> BatchItem:
        """转换"""
        await asyncio.sleep(0.3)

        # 转换数据
        transformed_data = item.data.upper().strip()

        return BatchItem(
            id=item.id,
            data=transformed_data,
            priority=item.priority,
            metadata={**(item.metadata or {}), "transformed": True}
        )

    async def _enrich(self, item: BatchItem) -> Dict:
        """丰富"""
        await asyncio.sleep(0.4)

        return {
            "id": item.id,
            "original_data": item.data,
            "processed_data": item.data,
            "metadata": item.metadata,
            "enrichment": {
                "word_count": len(item.data.split()),
                "char_count": len(item.data),
                "timestamp": time.time()
            }
        }


class IntelligentBatchProcessor:
    """智能批量处理器"""

    def __init__(self):
        self.success_count = 0
        self.failure_count = 0

    async def adaptive_batch_process(self, items: List[BatchItem]) -> List[Dict]:
        """自适应批量处理"""
        print(f"\n🧠 智能批量处理 {len(items)} 个项目")

        # 初始批次大小
        batch_size = 5
        max_batch_size = 20
        min_batch_size = 1

        results = []
        i = 0

        while i < len(items):
            current_batch = items[i:i + batch_size]

            print(f"\n📦 尝试批次大小: {batch_size} (项目 {i + 1}-{min(i + batch_size, len(items))})")

            try:
                # 处理当前批次
                batch_results = await self._process_batch_adaptive(current_batch)
                results.extend(batch_results)

                # 根据成功率调整批次大小
                success_rate = sum(1 for r in batch_results if r.get("success", False)) / len(batch_results)

                if success_rate > 0.9:
                    # 成功率高，增加批次大小
                    batch_size = min(batch_size + 2, max_batch_size)
                    print(f"  ✅ 成功率高 ({success_rate:.0%})，增加批次大小到 {batch_size}")
                elif success_rate < 0.7:
                    # 成功率低，减小批次大小
                    batch_size = max(batch_size - 1, min_batch_size)
                    print(f"  ⚠️  成功率低 ({success_rate:.0%})，减小批次大小到 {batch_size}")
                else:
                    print(f"  ✅ 成功率适中 ({success_rate:.0%})，保持批次大小 {batch_size}")

                i += len(current_batch)

            except Exception as e:
                print(f"  ❌ 批次处理失败: {e}")
                # 如果整个批次失败，减小批次大小重试
                batch_size = max(batch_size // 2, min_batch_size)
                print(f"  🔄 减小批次大小到 {batch_size} 重试")

        return results

    async def _process_batch_adaptive(self, batch: List[BatchItem]) -> List[Dict]:
        """自适应批次处理"""
        # 动态调整并发数
        concurrent_count = min(len(batch), 5)

        semaphore = asyncio.Semaphore(concurrent_count)
        tasks = [self._bounded_process_with_retry(item, semaphore) for item in batch]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [
            r if not isinstance(r, Exception) else {"id": item.id, "success": False, "error": str(r)}
            for item, r in zip(batch, results)
        ]

    async def _bounded_process_with_retry(self, item: BatchItem, semaphore: asyncio.Semaphore):
        """带重试的并发处理"""
        max_retries = 3

        for attempt in range(max_retries):
            try:
                async with semaphore:
                    return await self._process_item_with_metrics(item)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = 0.5 * (2 ** attempt)
                await asyncio.sleep(wait_time)

    async def _process_item_with_metrics(self, item: BatchItem) -> Dict:
        """处理项目并记录指标"""
        start_time = time.time()

        try:
            # 模拟处理
            await asyncio.sleep(0.5)

            result = {
                "id": item.id,
                "success": True,
                "data": item.data,
                "processing_time": time.time() - start_time,
                "timestamp": time.time()
            }

            self.success_count += 1
            return result

        except Exception as e:
            self.failure_count += 1
            raise


# 示例数据生成
def generate_sample_items(count: int) -> List[BatchItem]:
    """生成示例数据"""
    items = []
    for i in range(count):
        # 一些会失败的数据
        data = f"item_{i}"
        if i % 10 == 0:
            data = "error_data"  # 会触发错误

        items.append(BatchItem(
            id=f"item_{i:03d}",
            data=data,
            priority=i % 3,
            metadata={"batch": i // 10}
        ))
    return items


async def main():
    """主函数"""
    print("=" * 60)
    print("📦 ScholarFlow 批量处理示例")
    print("=" * 60)

    # 示例 1: 基础批量处理
    print("\n" + "=" * 60)
    print("📋 示例 1: 基础批量处理")
    print("=" * 60)

    processor = BatchProcessor(batch_size=3, max_workers=2)
    sample_items = generate_sample_items(15)

    results = await processor.process_all(sample_items)

    # 统计结果
    success_results = [r for r in results if r.get("success", False)]
    failure_results = [r for r in results if not r.get("success", False)]

    print(f"\n📊 处理统计:")
    print(f"  总项目: {len(results)}")
    print(f"  成功: {len(success_results)}")
    print(f"  失败: {len(failure_results)}")

    if failure_results:
        print(f"\n❌ 失败项目:")
        for result in failure_results[:5]:  # 只显示前5个
            print(f"  - {result['id']}: {result.get('error', 'Unknown error')}")

    # 示例 2: 管道处理
    print("\n" + "=" * 60)
    print("📋 示例 2: 管道处理")
    print("=" * 60)

    pipeline_processor = AdvancedBatchProcessor()
    pipeline_items = [
        BatchItem("p1", "hello world"),
        BatchItem("p2", "test"),
        BatchItem("p3", "valid data here"),
        BatchItem("p4", ""),  # 会失败
    ]

    pipeline_results = await pipeline_processor.process_with_pipeline(pipeline_items)

    print(f"\n✅ 管道处理完成: {len(pipeline_results)} 项目")

    # 示例 3: 智能自适应处理
    print("\n" + "=" * 60)
    print("📋 示例 3: 智能自适应处理")
    print("=" * 60)

    intelligent_processor = IntelligentBatchProcessor()
    large_dataset = generate_sample_items(50)

    print(f"\n🚀 开始智能处理...")
    start_time = time.time()

    intelligent_results = await intelligent_processor.adaptive_batch_process(large_dataset)

    total_time = time.time() - start_time

    # 最终统计
    final_success = sum(1 for r in intelligent_results if r.get("success", False))
    final_failure = len(intelligent_results) - final_success

    print(f"\n🎉 智能处理完成:")
    print(f"  总时间: {total_time:.2f} 秒")
    print(f"  总项目: {len(intelligent_results)}")
    print(f"  成功: {final_success}")
    print(f"  失败: {final_failure}")
    print(f"  成功率: {final_success / len(intelligent_results):.1%}")
    print(f"  平均速度: {len(intelligent_results) / total_time:.2f} 项目/秒")

    print("\n" + "=" * 60)
    print("✨ 批量处理示例完成!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())


"""
💡 学习要点:

1. 基础批量处理
   - 分批处理大量数据
   - 控制并发数量
   - 错误处理和恢复

2. 管道处理
   - 多阶段处理
   - 阶段间数据传递
   - 渐进式处理

3. 智能自适应处理
   - 动态调整批次大小
   - 根据成功率优化
   - 指数退避重试

4. 性能优化
   - 并发控制
   - 资源管理
   - 进度跟踪

📝 扩展练习:

1. 添加优先级队列
2. 实现分布式批量处理
3. 添加实时监控面板
4. 实现断点续传
5. 添加批量结果缓存

🔗 相关文档:

- asyncio: https://docs.python.org/3/library/asyncio.html
- concurrent.futures: https://docs.python.org/3/library/concurrent.futures.html
"""
