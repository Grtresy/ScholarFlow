'use client';

import React, { useEffect, useState } from 'react';
import { getTaskStatus, TaskStatus as ITaskStatus, TaskStatusResponse } from '@/lib/api';
import { useTaskStatusWebSocket, ConnectionStatus } from '@/lib/websocket';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { StepProgress } from '@/components/StepProgress';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

interface TaskStatusProps {
    taskId: string;
    onReviewRequired: (status: TaskStatusResponse) => void;
    onCompleted: (status: TaskStatusResponse) => void;
    restartPolling?: number; // Increment this to force polling restart (deprecated, kept for compatibility)
}

export function TaskStatus({ taskId, onReviewRequired, onCompleted, restartPolling }: TaskStatusProps) {
    // Use WebSocket hook for real-time updates
    const { status, error, connectionStatus } = useTaskStatusWebSocket(
        taskId,
        onReviewRequired,
        onCompleted,
        (err) => toast.error(err)
    );

    // Get connection status display info
    const getConnectionStatusInfo = (status: ConnectionStatus) => {
        switch (status) {
            case 'connecting':
                return { color: 'bg-yellow-500', text: '连接中...' };
            case 'connected':
                return { color: 'bg-green-500', text: '实时连接' };
            case 'reconnecting':
                return { color: 'bg-yellow-500', text: '重连中...' };
            case 'disconnected':
                return { color: 'bg-zinc-500', text: '已断开' };
            case 'error':
                return { color: 'bg-blue-500', text: '使用轮询' };
            default:
                return { color: 'bg-zinc-500', text: '未知' };
        }
    };

    const statusInfo = getConnectionStatusInfo(connectionStatus);

    if (error) {
        const isTaskNotFound = error.includes('不存在') || error.includes('不存在') || error.includes('TASK_NOT_FOUND');

        return (
            <Card className={`border-2 ${isTaskNotFound ? 'border-yellow-500 dark:border-yellow-600' : 'border-red-200 dark:border-red-900'}`}>
                <CardHeader>
                    <CardTitle className={`${isTaskNotFound ? 'text-yellow-600 dark:text-yellow-400' : 'text-red-600 dark:text-red-400'}`}>
                        {isTaskNotFound ? '⚠️ 任务不存在' : '处理失败'}
                    </CardTitle>
                    <CardDescription className="space-y-2">
                        <div>{error}</div>
                        {isTaskNotFound && (
                            <div className="mt-4 space-y-2">
                                <p className="text-sm text-zinc-600 dark:text-zinc-400">
                                    您可能：
                                </p>
                                <ul className="text-sm text-zinc-600 dark:text-zinc-400 list-disc list-inside space-y-1">
                                    <li>从书签或旧链接访问了不存在的任务</li>
                                    <li>任务已被删除或过期</li>
                                    <li>任务ID输入错误</li>
                                </ul>
                            </div>
                        )}
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {isTaskNotFound && (
                        <div className="mt-4">
                            <Button
                                onClick={() => window.location.href = '/'}
                                className="w-full"
                            >
                                返回首页创建新任务
                            </Button>
                        </div>
                    )}
                </CardContent>
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
                    {/* WebSocket connection status indicator */}
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center space-x-2">
                            <div className="relative flex h-3 w-3">
                                <span className={`absolute inline-flex h-full w-full animate-ping rounded-full ${statusInfo.color} opacity-75`} />
                                <span className={`relative inline-flex h-3 w-3 rounded-full ${statusInfo.color}`} />
                            </div>
                            <span className="text-xs text-zinc-500 dark:text-zinc-400">
                                {connectionStatus === 'connected' ? '实时连接' :
                                 connectionStatus === 'reconnecting' ? '重连中...' :
                                 connectionStatus === 'error' ? '连接错误，使用降级轮询' :
                                 connectionStatus === 'connecting' ? '连接中...' :
                                 '已断开'}
                            </span>
                        </div>

                        {/* Show fallback polling indicator */}
                        {connectionStatus === 'error' && (
                            <div className="flex items-center space-x-1 text-xs text-blue-600 dark:text-blue-400">
                                <span>🔄</span>
                                <span>使用轮询更新</span>
                            </div>
                        )}
                    </div>

                    {/* Task status */}
                    <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                            <span className="text-zinc-500 dark:text-zinc-400">当前步骤</span>
                            <span className="font-medium">{status.current_step}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                            <span className="text-zinc-500 dark:text-zinc-400">进度</span>
                            <span className="font-medium">{status.progress_percentage.toFixed(1)}%</span>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Step Progress Component */}
            <StepProgress status={status} />
        </div>
    );
}
