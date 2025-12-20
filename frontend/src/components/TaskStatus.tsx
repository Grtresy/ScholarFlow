'use client';

import React, { useEffect, useState } from 'react';
import { getTaskStatus, TaskStatus as ITaskStatus, TaskStatusResponse } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { StepProgress } from '@/components/StepProgress';
import { toast } from 'sonner';

interface TaskStatusProps {
    taskId: string;
    onReviewRequired: (status: TaskStatusResponse) => void;
    onCompleted: (status: TaskStatusResponse) => void;
    restartPolling?: number; // Increment this to force polling restart
}

export function TaskStatus({ taskId, onReviewRequired, onCompleted, restartPolling }: TaskStatusProps) {
    const [status, setStatus] = useState<TaskStatusResponse | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let intervalId: NodeJS.Timeout;
        let mounted = true;

        console.log('[DEBUG TaskStatus] useEffect running, taskId:', taskId, 'restartPolling:', restartPolling);

        const pollStatus = async () => {
            try {
                const response = await getTaskStatus(taskId);
                console.log('[DEBUG TaskStatus] Poll response status:', response.status);

                if (!mounted) return;

                setStatus(response);
                setError(null);

                // Check if review is needed
                if (response.needs_human_review && response.status === ITaskStatus.HUMAN_REVIEW) {
                    console.log('[DEBUG TaskStatus] Review needed, stopping poll');
                    clearInterval(intervalId);
                    onReviewRequired(response);
                    return;
                }

                // Check if completed
                if (response.status === ITaskStatus.COMPLETED) {
                    console.log('[DEBUG TaskStatus] Task completed!');
                    clearInterval(intervalId);
                    toast.success('任务完成！');
                    onCompleted(response);
                    return;
                }

                // Check if failed
                if (response.status === ITaskStatus.FAILED) {
                    console.log('[DEBUG TaskStatus] Task failed');
                    clearInterval(intervalId);
                    toast.error(response.error_message || '任务失败');
                    setError(response.error_message || '任务处理失败');
                    return;
                }
            } catch (err) {
                console.error('Status polling error:', err);
                if (mounted) {
                    setError(err instanceof Error ? err.message : '获取状态失败');
                }
            }
        };

        // Initial poll
        pollStatus();

        // Poll every 2 seconds
        intervalId = setInterval(pollStatus, 2000);

        return () => {
            mounted = false;
            clearInterval(intervalId);
        };
    }, [taskId, onReviewRequired, onCompleted, restartPolling]);

    if (error) {
        return (
            <Card className="border-red-200 dark:border-red-900">
                <CardHeader>
                    <CardTitle className="text-red-600 dark:text-red-400">处理失败</CardTitle>
                    <CardDescription>{error}</CardDescription>
                </CardHeader>
            </Card>
        );
    }

    if (!status) {
        return (
            <Card>
                <CardContent className="pt-6">
                    <div className="flex items-center justify-center space-x-2">
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-900 dark:border-zinc-700 dark:border-t-zinc-100" />
                        <p className="text-sm text-zinc-500 dark:text-zinc-400">加载中...</p>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-4">
            <Card>
                <CardHeader>
                    <CardTitle>任务信息</CardTitle>
                    <CardDescription>任务 ID: {status.task_id}</CardDescription>
                </CardHeader>
                <CardContent>
                    {/* Status indicator */}
                    <div className="flex items-center space-x-2 mb-4">
                        <div className="relative flex h-3 w-3">
                            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-blue-400 opacity-75" />
                            <span className="relative inline-flex h-3 w-3 rounded-full bg-blue-500" />
                        </div>
                        <span className="text-xs text-zinc-500 dark:text-zinc-400">处理中...</span>
                    </div>
                </CardContent>
            </Card>

            {/* Step Progress Component */}
            <StepProgress status={status} />
        </div>
    );
}
