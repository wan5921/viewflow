from django.test import TestCase

from viewflow import this
from viewflow.workflow import flow
from viewflow.workflow.status import STATUS


class TestSplitJoinBranches(TestCase):
    """测试 Split 节点遍历所有分支及 Join 节点正确计数"""

    def test_split_activates_all_branches(self):
        """验证 Split 节点激活所有分支"""
        process = ThreeBranchWorkflow.start.run()
        
        # 验证 Split 后创建了 3 个并行任务
        task_a = process.task_set.filter(flow_task=ThreeBranchWorkflow.task_a).first()
        task_b = process.task_set.filter(flow_task=ThreeBranchWorkflow.task_b).first()
        task_c = process.task_set.filter(flow_task=ThreeBranchWorkflow.task_c).first()
        
        self.assertIsNotNone(task_a)
        self.assertIsNotNone(task_b)
        self.assertIsNotNone(task_c)
        
        # 验证 Join 任务存在且状态为 STARTED
        join_task = process.task_set.filter(flow_task=ThreeBranchWorkflow.join).first()
        self.assertEqual(join_task.status, STATUS.STARTED)

    def test_join_waits_for_all_branches(self):
        """验证 Join 节点等待所有分支完成"""
        process = ThreeBranchWorkflow.start.run()
        
        # 完成第一个任务
        task_a = process.task_set.get(flow_task=ThreeBranchWorkflow.task_a)
        ThreeBranchWorkflow.task_a.run(task_a)
        
        # Join 应该仍然在 STARTED 状态
        join_task = process.task_set.get(flow_task=ThreeBranchWorkflow.join)
        join_task.refresh_from_db()
        self.assertEqual(join_task.status, STATUS.STARTED)
        
        # 完成第二个任务
        task_b = process.task_set.get(flow_task=ThreeBranchWorkflow.task_b)
        ThreeBranchWorkflow.task_b.run(task_b)
        
        # Join 应该仍然在 STARTED 状态
        join_task.refresh_from_db()
        self.assertEqual(join_task.status, STATUS.STARTED)
        
        # 完成第三个任务
        task_c = process.task_set.get(flow_task=ThreeBranchWorkflow.task_c)
        ThreeBranchWorkflow.task_c.run(task_c)
        
        # Join 应该完成
        join_task.refresh_from_db()
        self.assertEqual(join_task.status, STATUS.DONE)
        
        # 流程应该完成
        process.refresh_from_db()
        self.assertEqual(process.status, STATUS.DONE)

    def test_split_with_conditional_branches(self):
        """验证带条件的 Split 分支"""
        process = ConditionalWorkflow.start.run()
        
        # 只有 task_a 和 task_c 应该被激活（task_b 的条件为 False）
        task_a = process.task_set.filter(flow_task=ConditionalWorkflow.task_a).first()
        task_b = process.task_set.filter(flow_task=ConditionalWorkflow.task_b).first()
        task_c = process.task_set.filter(flow_task=ConditionalWorkflow.task_c).first()
        
        self.assertIsNotNone(task_a)
        self.assertIsNone(task_b)  # 条件不满足，不应创建
        self.assertIsNotNone(task_c)
        
        # 完成两个任务后 Join 应该完成
        ThreeBranchWorkflow.task_a.run(task_a)
        ThreeBranchWorkflow.task_c.run(task_c)
        
        join_task = process.task_set.get(flow_task=ConditionalWorkflow.join)
        join_task.refresh_from_db()
        self.assertEqual(join_task.status, STATUS.DONE)

    def test_parallel_task_count(self):
        """验证并行任务总数"""
        process = ThreeBranchWorkflow.start.run()
        
        # 总任务数应该是：start + split + task_a + task_b + task_c + join + end = 7
        total_tasks = process.task_set.count()
        self.assertEqual(total_tasks, 7)


class ThreeBranchWorkflow(flow.Flow):
    """具有三个并行分支的工作流"""
    
    start = flow.StartHandle().Next(this.split)
    
    split = (
        flow.Split()
        .Next(this.task_a)
        .Next(this.task_b)
        .Next(this.task_c)
    )
    
    task_a = flow.Function(this.func_a).Next(this.join)
    task_b = flow.Function(this.func_b).Next(this.join)
    task_c = flow.Function(this.func_c).Next(this.join)
    
    join = flow.Join().Next(this.end)
    
    end = flow.End()
    
    def func_a(self, activation):
        pass
    
    def func_b(self, activation):
        pass
    
    def func_c(self, activation):
        pass


class ConditionalWorkflow(flow.Flow):
    """带条件分支的工作流"""
    
    start = flow.StartHandle().Next(this.split)
    
    split = (
        flow.Split()
        .Next(this.task_a)
        .Next(this.task_b, case=lambda act: False)  # 永远不激活
        .Next(this.task_c)
    )
    
    task_a = flow.Function(this.func_a).Next(this.join)
    task_b = flow.Function(this.func_b).Next(this.join)
    task_c = flow.Function(this.func_c).Next(this.join)
    
    join = flow.Join().Next(this.end)
    
    end = flow.End()
    
    def func_a(self, activation):
        pass
    
    def func_b(self, activation):
        pass
    
    def func_c(self, activation):
        pass
