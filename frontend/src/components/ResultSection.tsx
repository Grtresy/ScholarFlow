'use client';

import React, { useState, useEffect } from 'react';
import { downloadPresentation, triggerDownload, getMarkdownContent, saveOriginalVersion, TaskStatusResponse } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ResultEditor } from '@/components/ResultEditor';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import { Edit3 } from 'lucide-react';

interface ResultSectionProps {
    taskStatus: TaskStatusResponse;
}

export function ResultSection({ taskStatus }: ResultSectionProps) {
    const [downloading, setDownloading] = useState(false);
    const [markdown, setMarkdown] = useState('');
    const [showEditor, setShowEditor] = useState(false);
    const [loading, setLoading] = useState(true);
    const [savingOriginal, setSavingOriginal] = useState(false);

    useEffect(() => {
        const fetchMarkdown = async () => {
            try {
                setLoading(true);
                const data = await getMarkdownContent(taskStatus.task_id, 'marp_markdown');
                setMarkdown(data.content || '');
            } catch (error) {
                console.error('Failed to fetch markdown:', error);
                toast.error('获取内容失败');
            } finally {
                setLoading(false);
            }
        };

        fetchMarkdown();
    }, [taskStatus.task_id]);

    const handleDownload = async () => {
        setDownloading(true);
        try {
            toast.info('正在下载...');
            const blob = await downloadPresentation(taskStatus.task_id);

            // Generate filename
            const timestamp = new Date().toISOString().split('T')[0];
            const filename = `presentation_${taskStatus.task_id}_${timestamp}.pptx`;

            triggerDownload(blob, filename);
            toast.success('下载成功！');
        } catch (error) {
            console.error('Download error:', error);
            toast.error(error instanceof Error ? error.message : '下载失败，请重试');
        } finally {
            setDownloading(false);
        }
    };

    const handleNewTask = () => {
        window.location.reload();
    };

    const handleShowEditor = async () => {
        setSavingOriginal(true);
        try {
            await saveOriginalVersion(taskStatus.task_id);
            toast.success('原始版本已保存');
        } catch (error) {
            console.error('Failed to save original version:', error);
            // Continue to editor even if save fails, just log the error
            toast.warning('保存原始版本失败，但仍可继续编辑');
        } finally {
            setSavingOriginal(false);
        }
        setShowEditor(true);
    };

    // Show editor if toggled
    if (showEditor) {
        if (loading) {
            return (
                <div className="max-w-5xl mx-auto">
                    <Card>
                        <CardContent className="pt-6">
                            <div className="flex items-center justify-center py-12">
                                <div className="text-center">
                                    <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent mx-auto mb-2" />
                                    <p className="text-sm text-zinc-500">加载中...</p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            );
        }

        return (
            <div className="max-w-5xl mx-auto space-y-4">
                <Card>
                    <CardHeader>
                        <div className="flex items-center justify-between">
                            <div>
                                <CardTitle>编辑演示文稿</CardTitle>
                                <CardDescription>任务 ID: {taskStatus.task_id}</CardDescription>
                            </div>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setShowEditor(false)}
                            >
                                返回
                            </Button>
                        </div>
                    </CardHeader>
                </Card>
                <ResultEditor
                    taskId={taskStatus.task_id}
                    initialMarkdown={markdown}
                    onSave={setMarkdown}
                />
            </div>
        );
    }

    return (
        <div className="max-w-3xl mx-auto space-y-6">
            {/* Success card */}
            <Card className="border-green-200 dark:border-green-900 bg-green-50 dark:bg-green-950/20">
                <CardHeader>
                    <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-green-100 dark:bg-green-900">
                            <svg
                                className="h-6 w-6 text-green-600 dark:text-green-400"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M5 13l4 4L19 7"
                                />
                            </svg>
                        </div>
                        <div>
                            <CardTitle className="text-green-900 dark:text-green-100">
                                生成完成！
                            </CardTitle>
                            <CardDescription className="text-green-700 dark:text-green-300">
                                您的演示文稿已准备就绪
                            </CardDescription>
                        </div>
                    </div>
                </CardHeader>
            </Card>

            {/* Task details */}
            <Card>
                <CardHeader>
                    <CardTitle>任务详情</CardTitle>
                    <CardDescription>任务 ID: {taskStatus.task_id}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-4 text-sm">
                        <div className="space-y-1">
                            <span className="text-zinc-500 dark:text-zinc-400">当前步骤</span>
                            <p className="font-medium text-zinc-900 dark:text-zinc-100">
                                {taskStatus.current_step}
                            </p>
                        </div>
                        <div className="space-y-1">
                            <span className="text-zinc-500 dark:text-zinc-400">完成进度</span>
                            <p className="font-medium text-zinc-900 dark:text-zinc-100">
                                {Math.round(taskStatus.progress_percentage)}%
                            </p>
                        </div>
                    </div>

                    <Separator />

                    <div className="grid grid-cols-2 gap-4 text-sm">
                        <div className="space-y-1">
                            <span className="text-zinc-500 dark:text-zinc-400">创建时间</span>
                            <p className="text-zinc-700 dark:text-zinc-300">
                                {new Date(taskStatus.created_at).toLocaleString('zh-CN')}
                            </p>
                        </div>
                        <div className="space-y-1">
                            <span className="text-zinc-500 dark:text-zinc-400">完成时间</span>
                            <p className="text-zinc-700 dark:text-zinc-300">
                                {new Date(taskStatus.updated_at).toLocaleString('zh-CN')}
                            </p>
                        </div>
                    </div>

                    <Separator />

                    {/* Processing stats */}
                    {taskStatus.review_points && taskStatus.review_points.length > 0 && (
                        <div className="space-y-1">
                            <span className="text-zinc-500 dark:text-zinc-400 text-sm">审核要点</span>
                            <p className="text-zinc-700 dark:text-zinc-300">
                                {taskStatus.review_points.length} 个审核点
                            </p>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Action buttons */}
            <div className="grid grid-cols-2 gap-3">
                <Button
                    onClick={handleShowEditor}
                    disabled={savingOriginal}
                    variant="default"
                    size="lg"
                    className="flex-1"
                >
                    {savingOriginal ? (
                        <>
                            <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                            保存中...
                        </>
                    ) : (
                        <>
                            <Edit3 className="mr-2 h-4 w-4" />
                            编辑演示文稿
                        </>
                    )}
                </Button>
                <Button
                    onClick={handleDownload}
                    disabled={downloading}
                    variant="outline"
                    size="lg"
                    className="flex-1"
                >
                    {downloading ? (
                        <>
                            <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-zinc-600 border-t-transparent" />
                            下载中...
                        </>
                    ) : (
                        <>
                            <svg
                                className="mr-2 h-4 w-4"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                                />
                            </svg>
                            下载 PPT
                        </>
                    )}
                </Button>
            </div>
            <Button
                onClick={handleNewTask}
                variant="ghost"
                size="lg"
                className="w-full"
            >
                <svg
                    className="mr-2 h-4 w-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 4v16m8-8H4"
                    />
                </svg>
                新建任务
            </Button>

            {/* Tips */}
            <Card className="bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-900">
                <CardContent className="pt-6">
                    <div className="flex gap-3">
                        <svg
                            className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                            />
                        </svg>
                        <div className="space-y-1 text-sm">
                            <p className="font-medium text-blue-900 dark:text-blue-100">提示</p>
                            <p className="text-blue-700 dark:text-blue-300">
                                生成的演示文稿为 PowerPoint 格式（.pptx），您可以使用 Microsoft PowerPoint、
                                WPS 或其他兼容软件打开和编辑。
                            </p>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
