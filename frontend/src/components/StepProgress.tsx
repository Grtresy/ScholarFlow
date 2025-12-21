'use client';

import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Progress } from '@/components/ui/progress';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { CheckCircle, Circle, Clock, FileText, Image, Cpu } from 'lucide-react';
import { TaskStatusResponse } from '@/lib/api';
import { WorkflowWebSocketClient, ConnectionStatus } from '@/lib/websocket';

interface StepProgressProps {
    status: TaskStatusResponse;
}

interface WorkflowStep {
    key: string;
    label: string;
    status: 'completed' | 'current' | 'pending' | 'error';
    progress?: number;
    details?: string;
}

interface ChunkProgressInfo {
    chunk_index: number;
    total_chunks: number;
    completed_chunks: number;
    current_chunk_content?: string;
    timestamp: number;
}

interface RenderProgressInfo {
    stage: string;
    percentage: number;
    output_format: string;
    timestamp: number;
}

const STATUS_LABELS: Record<string, string> = {
    'PENDING': '等待中',
    'INITIALIZING': '初始化',
    'PARSING': '解析 PDF',
    'SPLITTING': '分割文本',
    'STAGE1_PROCESSING': '生成大纲',
    'MERGING': '合并大纲',
    'HUMAN_REVIEW': '等待审核',
    'STAGE2_PROCESSING': '生成演示文稿',
    'RENDERING': '渲染输出',
    'COMPLETED': '完成',
    'FAILED': '失败',
    'PAUSED': '暂停',
};

export function StepProgress({ status }: StepProgressProps) {
    const [chunkProgress, setChunkProgress] = useState<ChunkProgressInfo | null>(null);
    const [renderProgress, setRenderProgress] = useState<RenderProgressInfo | null>(null);
    const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');

    // WebSocket connection for real-time progress
    useEffect(() => {
        if (!status.task_id) return;

        const wsClient = new WorkflowWebSocketClient(status.task_id);

        // Connection status handler
        wsClient.onStatusChange((status) => {
            setConnectionStatus(status);
        });

        // Chunk progress handler
        wsClient.onChunkProgress((data) => {
            console.log('[StepProgress] Chunk progress:', data);
            setChunkProgress({
                ...data,
                timestamp: Date.now()
            });
        });

        // Render progress handler
        wsClient.onRenderProgress((data) => {
            console.log('[StepProgress] Render progress:', data);
            setRenderProgress({
                ...data,
                timestamp: Date.now()
            });
        });

        // Connect
        wsClient.connect();

        return () => {
            wsClient.disconnect();
        };
    }, [status.task_id]);

    // Build workflow steps based on current status
    const buildWorkflowSteps = (): WorkflowStep[] => {
        const steps: WorkflowStep[] = [
            {
                key: 'init',
                label: '初始化',
                status: status.created_at ? 'completed' : 'pending',
                details: '验证输入参数',
            },
            {
                key: 'parse',
                label: 'PDF 解析',
                status: getStepStatus(['INITIALIZING', 'PARSING'], ['SPLITTING', 'STAGE1_PROCESSING', 'MERGING', 'HUMAN_REVIEW', 'STAGE2_PROCESSING', 'RENDERING', 'COMPLETED']),
                details: '提取文本和图像',
            },
            {
                key: 'split',
                label: '文本分割',
                status: getStepStatus(['PARSING', 'SPLITTING'], ['STAGE1_PROCESSING', 'MERGING', 'HUMAN_REVIEW', 'STAGE2_PROCESSING', 'RENDERING', 'COMPLETED']),
                details: '分块处理内容',
            },
            {
                key: 'stage1',
                label: '生成大纲',
                status: getStepStatus(['SPLITTING', 'STAGE1_PROCESSING'], ['MERGING', 'HUMAN_REVIEW', 'STAGE2_PROCESSING', 'RENDERING', 'COMPLETED']),
                progress: status.stage1_completed && status.stage1_total
                    ? (status.stage1_completed / status.stage1_total) * 100
                    : undefined,
                details: status.stage1_completed && status.stage1_total
                    ? `处理 ${status.stage1_completed}/${status.stage1_total} 个块`
                    : '处理内容块',
            },
            {
                key: 'merge',
                label: '合并大纲',
                status: getStepStatus(['STAGE1_PROCESSING', 'MERGING'], ['HUMAN_REVIEW', 'STAGE2_PROCESSING', 'RENDERING', 'COMPLETED']),
                details: '整合所有内容',
            },
            {
                key: 'review',
                label: '人工审核',
                status: getStepStatus(['MERGING', 'HUMAN_REVIEW'], ['STAGE2_PROCESSING', 'RENDERING', 'COMPLETED']),
                details: '用户确认内容',
            },
            {
                key: 'stage2',
                label: '生成演示',
                status: getStepStatus(['HUMAN_REVIEW', 'STAGE2_PROCESSING'], ['RENDERING', 'COMPLETED']),
                details: '创建 Marp 文档',
            },
            {
                key: 'render',
                label: '渲染输出',
                status: getStepStatus(['STAGE2_PROCESSING', 'RENDERING'], ['COMPLETED']),
                details: '生成 PPT/PDF',
            },
        ];

        return steps;
    };

    const getStepStatus = (completedStatuses: string[], currentStatuses: string[]): 'completed' | 'current' | 'pending' | 'error' => {
        if (status.status === 'FAILED') {
            return 'error';
        }
        if (completedStatuses.includes(status.status)) {
            return 'current';
        }
        if (currentStatuses.includes(status.status) || ['COMPLETED'].includes(status.status)) {
            return 'completed';
        }
        return 'pending';
    };

    const steps = buildWorkflowSteps();
    const currentStepIndex = steps.findIndex(s => s.status === 'current');
    const completedSteps = steps.filter(s => s.status === 'completed').length;

    return (
        <div className="space-y-6">
            {/* Main Progress Bar */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-lg">任务进度</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="space-y-2">
                        <div className="flex justify-between items-center">
                            <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                                {STATUS_LABELS[status.status] || status.status}
                            </span>
                            <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                                {Math.round(status.progress_percentage)}%
                            </span>
                        </div>
                        <div className="relative">
                            <Progress value={status.progress_percentage} className="h-3" />
                            <motion.div
                                className="absolute top-0 left-0 h-3 bg-blue-500 rounded-full"
                                initial={{ width: 0 }}
                                animate={{ width: `${status.progress_percentage}%` }}
                                transition={{ duration: 0.5, ease: 'easeOut' }}
                            />
                        </div>
                    </div>

                    {/* Current Step Details */}
                    {status.current_step && (
                        <div className="bg-zinc-50 dark:bg-zinc-900 p-3 rounded-lg">
                            <p className="text-sm text-zinc-600 dark:text-zinc-400">
                                <span className="font-medium">当前步骤：</span>
                                {status.current_step}
                            </p>
                            {status.step_details && typeof status.step_details === 'object' && (
                                <div className="mt-2 text-xs text-zinc-500 dark:text-zinc-500">
                                    {Object.entries(status.step_details).map(([key, value]) => (
                                        <div key={key} className="flex gap-2">
                                            <span className="font-medium">{key}:</span>
                                            <span>{String(value)}</span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Real-time Progress Details */}
            {(chunkProgress || renderProgress) && (
                <Card className="border-blue-200 dark:border-blue-900">
                    <CardHeader>
                        <CardTitle className="text-lg flex items-center gap-2">
                            <Cpu className="w-5 h-5 text-blue-500" />
                            实时进度
                            {connectionStatus === 'connected' && (
                                <span className="text-xs bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 px-2 py-1 rounded-full">
                                    实时
                                </span>
                            )}
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {/* Chunk Progress */}
                        {chunkProgress && (
                            <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <FileText className="w-4 h-4 text-blue-500" />
                                        <span className="text-sm font-medium">Stage 1: 处理Chunk</span>
                                    </div>
                                    <span className="text-xs text-zinc-500">
                                        {chunkProgress.completed_chunks}/{chunkProgress.total_chunks}
                                    </span>
                                </div>
                                <Progress
                                    value={(chunkProgress.completed_chunks / chunkProgress.total_chunks) * 100}
                                    className="h-2"
                                />
                                {chunkProgress.current_chunk_content && (
                                    <div className="bg-zinc-50 dark:bg-zinc-900 p-2 rounded text-xs text-zinc-600 dark:text-zinc-400">
                                        <span className="font-medium">当前chunk预览：</span>
                                        <span className="block mt-1 truncate">
                                            {chunkProgress.current_chunk_content}
                                        </span>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Render Progress */}
                        {renderProgress && (
                            <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <Image className="w-4 h-4 text-purple-500" />
                                        <span className="text-sm font-medium">
                                            渲染: {renderProgress.stage}
                                        </span>
                                    </div>
                                    <span className="text-xs text-zinc-500">
                                        {Math.round(renderProgress.percentage)}%
                                    </span>
                                </div>
                                <Progress
                                    value={renderProgress.percentage}
                                    className="h-2"
                                />
                                <div className="flex items-center gap-2 text-xs text-zinc-500">
                                    <span>输出格式:</span>
                                    <span className="font-medium">{renderProgress.output_format.toUpperCase()}</span>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>
            )}

            {/* Step Timeline */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-lg">执行流程</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="relative">
                        {/* Timeline line */}
                        <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-zinc-200 dark:bg-zinc-800" />

                        {/* Steps */}
                        <div className="space-y-6">
                            {steps.map((step, index) => (
                                <motion.div
                                    key={step.key}
                                    initial={{ opacity: 0, x: -20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: index * 0.1 }}
                                    className="relative flex items-start gap-4"
                                >
                                    {/* Step icon */}
                                    <div className="relative z-10 flex items-center justify-center w-12 h-12 rounded-full bg-white dark:bg-zinc-950 border-2 border-zinc-200 dark:border-zinc-800">
                                        {step.status === 'completed' && (
                                            <CheckCircle className="w-6 h-6 text-green-500" />
                                        )}
                                        {step.status === 'current' && (
                                            <motion.div
                                                animate={{ rotate: 360 }}
                                                transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                                            >
                                                <Clock className="w-6 h-6 text-blue-500" />
                                            </motion.div>
                                        )}
                                        {step.status === 'error' && (
                                            <Circle className="w-6 h-6 text-red-500" />
                                        )}
                                        {step.status === 'pending' && (
                                            <Circle className="w-6 h-6 text-zinc-300 dark:text-zinc-700" />
                                        )}
                                    </div>

                                    {/* Step content */}
                                    <div className="flex-1 min-w-0 pb-4">
                                        <div className="flex items-center gap-2">
                                            <h4 className={`text-sm font-medium ${
                                                step.status === 'completed'
                                                    ? 'text-green-700 dark:text-green-400'
                                                    : step.status === 'current'
                                                    ? 'text-blue-700 dark:text-blue-400'
                                                    : step.status === 'error'
                                                    ? 'text-red-700 dark:text-red-400'
                                                    : 'text-zinc-400 dark:text-zinc-600'
                                            }`}>
                                                {step.label}
                                            </h4>
                                            {step.progress !== undefined && (
                                                <span className="text-xs text-zinc-500 dark:text-zinc-400">
                                                    ({Math.round(step.progress)}%)
                                                </span>
                                            )}
                                        </div>
                                        <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
                                            {step.details}
                                        </p>

                                        {/* Progress bar for current step */}
                                        {step.status === 'current' && step.progress !== undefined && (
                                            <div className="mt-2">
                                                <Progress value={step.progress} className="h-1" />
                                            </div>
                                        )}
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Timestamps */}
            <Card className="bg-zinc-50 dark:bg-zinc-900">
                <CardContent className="pt-6">
                    <div className="grid grid-cols-2 gap-4 text-xs text-zinc-500 dark:text-zinc-400">
                        <div>
                            <span className="block font-medium mb-1">创建时间</span>
                            <span>{new Date(status.created_at).toLocaleString('zh-CN')}</span>
                        </div>
                        <div>
                            <span className="block font-medium mb-1">更新时间</span>
                            <span>{new Date(status.updated_at).toLocaleString('zh-CN')}</span>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
