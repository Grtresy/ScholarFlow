'use client';

import React, { useState } from 'react';
import { submitHumanFeedback, TaskStatusResponse } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { MarkdownPreview } from '@/components/MarkdownPreview';
import { toast } from 'sonner';
import { FileText, Eye } from 'lucide-react';

interface ReviewSectionProps {
    taskStatus: TaskStatusResponse;
    onReviewed: () => void;
}

export function ReviewSection({ taskStatus, onReviewed }: ReviewSectionProps) {
    const [comments, setComments] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [submitted, setSubmitted] = useState(false);
    const [selectedAction, setSelectedAction] = useState<'approve' | 'regenerate' | 'abort'>('approve');
    const [viewMode, setViewMode] = useState<'raw' | 'rendered'>('rendered');

    const handleSubmit = async () => {
        if (submitted) return; // Prevent duplicate submissions

        setSubmitted(true);
        setSubmitting(true);
        try {
            const feedback = {
                approved: selectedAction === 'approve',
                action: selectedAction === 'approve' ? undefined : selectedAction,
                comments: comments.trim() || undefined,
            };

            await submitHumanFeedback(taskStatus.task_id, feedback);

            if (selectedAction === 'approve') {
                toast.success('已批准，继续处理');
            } else if (selectedAction === 'regenerate') {
                toast.info('已请求重新生成');
            } else {
                toast.info('任务已终止');
            }

            onReviewed();
        } catch (error) {
            console.error('Feedback submission error:', error);
            toast.error(error instanceof Error ? error.message : '提交失败，请重试');
            setSubmitted(false); // Allow retry on error
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="max-w-4xl mx-auto space-y-6">
            <Card>
                <CardHeader>
                    <CardTitle>人工审核</CardTitle>
                    <CardDescription>
                        任务 {taskStatus.task_id} 需要您的审核
                    </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    {/* Review points */}
                    {taskStatus.review_points && taskStatus.review_points.length > 0 && (
                        <div className="space-y-4">
                            <div className="flex items-center justify-between">
                                <h3 className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                                    审核要点
                                </h3>
                                <div className="flex items-center gap-2">
                                    <Button
                                        variant={viewMode === 'raw' ? 'default' : 'ghost'}
                                        size="sm"
                                        onClick={() => setViewMode('raw')}
                                        className="h-8"
                                    >
                                        <FileText className="h-3 w-3 mr-1" />
                                        原始
                                    </Button>
                                    <Button
                                        variant={viewMode === 'rendered' ? 'default' : 'ghost'}
                                        size="sm"
                                        onClick={() => setViewMode('rendered')}
                                        className="h-8"
                                    >
                                        <Eye className="h-3 w-3 mr-1" />
                                        渲染
                                    </Button>
                                </div>
                            </div>
                            <div className="space-y-3">
                                {taskStatus.review_points.map((point, index) => (
                                    <Card key={index} className="bg-zinc-50 dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800">
                                        <CardContent className="pt-4 space-y-2">
                                            <div className="flex items-start justify-between">
                                                <div className="space-y-1 flex-1">
                                                    <div className="flex items-center gap-2">
                                                        <span className="inline-flex items-center rounded-md bg-blue-50 dark:bg-blue-950 px-2 py-1 text-xs font-medium text-blue-700 dark:text-blue-300 ring-1 ring-inset ring-blue-700/10 dark:ring-blue-300/10">
                                                            {point.type}
                                                        </span>
                                                        <span className="text-xs text-zinc-500 dark:text-zinc-400">
                                                            {point.node}
                                                        </span>
                                                    </div>
                                                    {viewMode === 'rendered' ? (
                                                        <div className="bg-white dark:bg-zinc-950 p-4 rounded border border-zinc-200 dark:border-zinc-700 max-h-96 overflow-auto">
                                                            <MarkdownPreview content={point.content} maxHeight="300px" />
                                                        </div>
                                                    ) : (
                                                        <pre className="text-sm text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap bg-white dark:bg-zinc-950 p-4 rounded border border-zinc-200 dark:border-zinc-700 max-h-96 overflow-auto font-mono text-xs">
                                                            {point.content}
                                                        </pre>
                                                    )}
                                                    {point.prompt && (
                                                        <details className="text-xs text-zinc-500 dark:text-zinc-400">
                                                            <summary className="cursor-pointer hover:text-zinc-700 dark:hover:text-zinc-300">
                                                                查看提示词
                                                            </summary>
                                                            <pre className="mt-2 p-2 bg-zinc-100 dark:bg-zinc-800 rounded overflow-x-auto">
                                                                {point.prompt}
                                                            </pre>
                                                        </details>
                                                    )}
                                                </div>
                                            </div>
                                            <p className="text-xs text-zinc-400 dark:text-zinc-500">
                                                {new Date(point.timestamp).toLocaleString('zh-CN')}
                                            </p>
                                        </CardContent>
                                    </Card>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Action tabs */}
                    <Tabs value={selectedAction} onValueChange={(v) => setSelectedAction(v as any)}>
                        <TabsList className="grid w-full grid-cols-3">
                            <TabsTrigger value="approve">批准</TabsTrigger>
                            <TabsTrigger value="regenerate">重新生成</TabsTrigger>
                            <TabsTrigger value="abort">终止</TabsTrigger>
                        </TabsList>

                        <TabsContent value="approve" className="space-y-4">
                            <p className="text-sm text-zinc-600 dark:text-zinc-400">
                                批准当前结果，继续后续处理步骤
                            </p>
                        </TabsContent>

                        <TabsContent value="regenerate" className="space-y-4">
                            <p className="text-sm text-zinc-600 dark:text-zinc-400">
                                重新生成当前步骤的结果
                            </p>
                        </TabsContent>

                        <TabsContent value="abort" className="space-y-4">
                            <p className="text-sm text-red-600 dark:text-red-400">
                                终止任务处理，不会继续后续步骤
                            </p>
                        </TabsContent>
                    </Tabs>

                    {/* Comments */}
                    <div className="space-y-2">
                        <label className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                            备注（可选）
                        </label>
                        <Textarea
                            placeholder="添加您的意见或建议..."
                            value={comments}
                            onChange={(e) => setComments(e.target.value)}
                            rows={4}
                            className="resize-none"
                        />
                    </div>

                    {/* Submit button */}
                    <Button
                        onClick={handleSubmit}
                        disabled={submitting || submitted}
                        className="w-full"
                        variant={selectedAction === 'abort' ? 'destructive' : 'default'}
                    >
                        {submitted ? '已提交' : submitting ? '提交中...' : '提交审核结果'}
                    </Button>
                </CardContent>
            </Card>

            {/* Task info */}
            <Card className="bg-zinc-50 dark:bg-zinc-900">
                <CardHeader>
                    <CardTitle className="text-sm">任务信息</CardTitle>
                </CardHeader>
                <CardContent className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                        <span className="text-zinc-500 dark:text-zinc-400">任务 ID</span>
                        <p className="font-mono text-xs">{taskStatus.task_id}</p>
                    </div>
                    <div>
                        <span className="text-zinc-500 dark:text-zinc-400">当前步骤</span>
                        <p>{taskStatus.current_step}</p>
                    </div>
                    <div>
                        <span className="text-zinc-500 dark:text-zinc-400">进度</span>
                        <p>{Math.round(taskStatus.progress_percentage)}%</p>
                    </div>
                    <div>
                        <span className="text-zinc-500 dark:text-zinc-400">更新时间</span>
                        <p className="text-xs">{new Date(taskStatus.updated_at).toLocaleString('zh-CN')}</p>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
