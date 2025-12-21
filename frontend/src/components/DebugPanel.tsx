'use client';

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Copy, Search, ChevronDown, ChevronRight, Clock, HardDrive, Network, Wifi } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { TaskStatusResponse } from '@/lib/api';
import { WorkflowWebSocketClient, ConnectionStatus } from '@/lib/websocket';
import ReactMarkdown from 'react-markdown';

interface DebugPanelProps {
    isOpen: boolean;
    onToggle: () => void;
    taskStatus: TaskStatusResponse | null;
}

interface NetworkRequest {
    url: string;
    method: string;
    status?: number;
    duration?: number;
    timestamp: string;
}

export function DebugPanel({ isOpen, onToggle, taskStatus }: DebugPanelProps) {
    const [searchTerm, setSearchTerm] = useState('');
    const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['workflowState']));
    const [activeTab, setActiveTab] = useState('state');
    const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
    const [websocketMessages, setWebsocketMessages] = useState<Array<{type: string, data: any, timestamp: number}>>([]);

    // WebSocket connection for monitoring
    useEffect(() => {
        if (!taskStatus?.task_id) return;

        const wsClient = new WorkflowWebSocketClient(taskStatus.task_id);

        // Connection status handler
        wsClient.onStatusChange((status) => {
            setConnectionStatus(status);
        });

        // Message handler
        wsClient.on('message', (message) => {
            setWebsocketMessages(prev => [...prev.slice(-99), message]); // Keep last 100 messages
        });

        // Connect
        wsClient.connect();

        return () => {
            wsClient.disconnect();
        };
    }, [taskStatus?.task_id]);

    // Mock data for execution time and memory (in real implementation, these would come from the backend)
    const executionStats = {
        totalDuration: taskStatus ? Date.now() - new Date(taskStatus.created_at).getTime() : 0,
        memoryUsage: '128 MB',
        networkRequests: [
            {
                url: '/api/tasks',
                method: 'POST',
                status: 200,
                duration: 450,
                timestamp: new Date().toISOString(),
            },
            {
                url: `/api/tasks/${taskStatus?.task_id}/status`,
                method: 'GET',
                status: 200,
                duration: 120,
                timestamp: new Date().toISOString(),
            },
        ] as NetworkRequest[],
    };

    const toggleSection = (section: string) => {
        const newExpanded = new Set(expandedSections);
        if (newExpanded.has(section)) {
            newExpanded.delete(section);
        } else {
            newExpanded.add(section);
        }
        setExpandedSections(newExpanded);
    };

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text);
        // You could add a toast notification here
    };

    const formatJSON = (obj: any) => {
        return JSON.stringify(obj, null, 2);
    };

    const filterContent = (content: string) => {
        if (!searchTerm) return content;
        return content.toLowerCase().includes(searchTerm.toLowerCase());
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Backdrop */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onToggle}
                        className="fixed inset-0 bg-black/50 z-40"
                    />

                    {/* Panel */}
                    <motion.div
                        initial={{ x: '100%' }}
                        animate={{ x: 0 }}
                        exit={{ x: '100%' }}
                        transition={{ type: 'spring', damping: 30, stiffness: 300 }}
                        className="fixed right-0 top-0 h-full w-[600px] bg-white dark:bg-zinc-950 shadow-2xl z-50 flex flex-col"
                    >
                        {/* Header */}
                        <div className="flex items-center justify-between p-4 border-b border-zinc-200 dark:border-zinc-800">
                            <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
                                调试面板
                            </h2>
                            <Button variant="ghost" size="sm" onClick={onToggle}>
                                <X className="h-4 w-4" />
                            </Button>
                        </div>

                        {/* Search */}
                        <div className="p-4 border-b border-zinc-200 dark:border-zinc-800">
                            <div className="relative">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-400" />
                                <Input
                                    placeholder="搜索调试信息..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    className="pl-10"
                                />
                            </div>
                        </div>

                        {/* Content */}
                        <div className="flex-1 overflow-auto p-4">
                            <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full">
                                <TabsList className="grid w-full grid-cols-5">
                                    <TabsTrigger value="state">状态</TabsTrigger>
                                    <TabsTrigger value="performance">性能</TabsTrigger>
                                    <TabsTrigger value="network">网络</TabsTrigger>
                                    <TabsTrigger value="websocket">WebSocket</TabsTrigger>
                                    <TabsTrigger value="logs">日志</TabsTrigger>
                                </TabsList>

                                {/* State Tab */}
                                <TabsContent value="state" className="space-y-4 mt-4">
                                    {/* Workflow State */}
                                    <Card>
                                        <CardHeader
                                            className="cursor-pointer"
                                            onClick={() => toggleSection('workflowState')}
                                        >
                                            <div className="flex items-center justify-between">
                                                <CardTitle className="text-sm">工作流状态</CardTitle>
                                                {expandedSections.has('workflowState') ? (
                                                    <ChevronDown className="h-4 w-4" />
                                                ) : (
                                                    <ChevronRight className="h-4 w-4" />
                                                )}
                                            </div>
                                        </CardHeader>
                                        {expandedSections.has('workflowState') && (
                                            <CardContent className="pt-0">
                                                <div className="relative">
                                                    <pre className="text-xs bg-zinc-100 dark:bg-zinc-900 p-3 rounded-lg overflow-auto max-h-96">
                                                        <code className="text-zinc-800 dark:text-zinc-200">
                                                            {taskStatus ? formatJSON(taskStatus) : '无数据'}
                                                        </code>
                                                    </pre>
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        className="absolute top-2 right-2"
                                                        onClick={() => copyToClipboard(formatJSON(taskStatus))}
                                                    >
                                                        <Copy className="h-3 w-3" />
                                                    </Button>
                                                </div>
                                            </CardContent>
                                        )}
                                    </Card>

                                    {/* Current Step Details */}
                                    <Card>
                                        <CardHeader
                                            className="cursor-pointer"
                                            onClick={() => toggleSection('currentStep')}
                                        >
                                            <div className="flex items-center justify-between">
                                                <CardTitle className="text-sm">当前步骤</CardTitle>
                                                {expandedSections.has('currentStep') ? (
                                                    <ChevronDown className="h-4 w-4" />
                                                ) : (
                                                    <ChevronRight className="h-4 w-4" />
                                                )}
                                            </div>
                                        </CardHeader>
                                        {expandedSections.has('currentStep') && (
                                            <CardContent className="pt-0">
                                                <div className="space-y-2 text-xs">
                                                    <div>
                                                        <span className="font-medium text-zinc-500">步骤：</span>
                                                        <span className="ml-2">{taskStatus?.current_step || '无'}</span>
                                                    </div>
                                                    <div>
                                                        <span className="font-medium text-zinc-500">进度：</span>
                                                        <span className="ml-2">
                                                            {taskStatus ? Math.round(taskStatus.progress_percentage) : 0}%
                                                        </span>
                                                    </div>
                                                    {taskStatus?.step_details && (
                                                        <div className="mt-2">
                                                            <span className="font-medium text-zinc-500">详情：</span>
                                                            <pre className="mt-1 bg-zinc-100 dark:bg-zinc-900 p-2 rounded text-xs overflow-auto">
                                                                {formatJSON(taskStatus.step_details)}
                                                            </pre>
                                                        </div>
                                                    )}
                                                </div>
                                            </CardContent>
                                        )}
                                    </Card>

                                    {/* Review Points */}
                                    {taskStatus?.review_points && taskStatus.review_points.length > 0 && (
                                        <Card>
                                            <CardHeader
                                                className="cursor-pointer"
                                                onClick={() => toggleSection('reviewPoints')}
                                            >
                                                <div className="flex items-center justify-between">
                                                    <CardTitle className="text-sm">
                                                        审核要点 ({taskStatus.review_points.length})
                                                    </CardTitle>
                                                    {expandedSections.has('reviewPoints') ? (
                                                        <ChevronDown className="h-4 w-4" />
                                                    ) : (
                                                        <ChevronRight className="h-4 w-4" />
                                                    )}
                                                </div>
                                            </CardHeader>
                                            {expandedSections.has('reviewPoints') && (
                                                <CardContent className="pt-0 space-y-3">
                                                    {taskStatus.review_points.map((point, index) => (
                                                        <div key={index} className="text-xs bg-zinc-50 dark:bg-zinc-900 p-3 rounded">
                                                            <div className="flex items-center gap-2 mb-2">
                                                                <span className="font-medium text-blue-600 dark:text-blue-400">
                                                                    {point.type}
                                                                </span>
                                                                <span className="text-zinc-500">•</span>
                                                                <span className="text-zinc-500">{point.node}</span>
                                                            </div>
                                                            <pre className="whitespace-pre-wrap text-zinc-700 dark:text-zinc-300">
                                                                {point.content}
                                                            </pre>
                                                            {point.prompt && (
                                                                <details className="mt-2">
                                                                    <summary className="cursor-pointer text-zinc-500">
                                                                        查看提示词
                                                                    </summary>
                                                                    <pre className="mt-1 bg-zinc-200 dark:bg-zinc-800 p-2 rounded text-xs overflow-auto">
                                                                        {point.prompt}
                                                                    </pre>
                                                                </details>
                                                            )}
                                                        </div>
                                                    ))}
                                                </CardContent>
                                            )}
                                        </Card>
                                    )}
                                </TabsContent>

                                {/* Performance Tab */}
                                <TabsContent value="performance" className="space-y-4 mt-4">
                                    <Card>
                                        <CardHeader>
                                            <CardTitle className="text-sm flex items-center gap-2">
                                                <Clock className="h-4 w-4" />
                                                执行时间
                                            </CardTitle>
                                        </CardHeader>
                                        <CardContent>
                                            <div className="space-y-2 text-xs">
                                                <div className="flex justify-between">
                                                    <span className="text-zinc-500">总耗时：</span>
                                                    <span className="font-medium">
                                                        {Math.round(executionStats.totalDuration / 1000)} 秒
                                                    </span>
                                                </div>
                                                <div className="flex justify-between">
                                                    <span className="text-zinc-500">当前步骤耗时：</span>
                                                    <span className="font-medium">
                                                        {taskStatus ? Math.round((Date.now() - new Date(taskStatus.updated_at).getTime()) / 1000) : 0} 秒
                                                    </span>
                                                </div>
                                            </div>
                                        </CardContent>
                                    </Card>

                                    <Card>
                                        <CardHeader>
                                            <CardTitle className="text-sm flex items-center gap-2">
                                                <HardDrive className="h-4 w-4" />
                                                内存使用
                                            </CardTitle>
                                        </CardHeader>
                                        <CardContent>
                                            <div className="space-y-2 text-xs">
                                                <div className="flex justify-between">
                                                    <span className="text-zinc-500">当前使用：</span>
                                                    <span className="font-medium">{executionStats.memoryUsage}</span>
                                                </div>
                                                <div className="w-full bg-zinc-200 dark:bg-zinc-800 rounded-full h-2">
                                                    <div
                                                        className="bg-blue-500 h-2 rounded-full"
                                                        style={{ width: '60%' }}
                                                    />
                                                </div>
                                            </div>
                                        </CardContent>
                                    </Card>
                                </TabsContent>

                                {/* Network Tab */}
                                <TabsContent value="network" className="space-y-4 mt-4">
                                    <Card>
                                        <CardHeader>
                                            <CardTitle className="text-sm flex items-center gap-2">
                                                <Network className="h-4 w-4" />
                                                网络请求
                                            </CardTitle>
                                        </CardHeader>
                                        <CardContent>
                                            <div className="space-y-2">
                                                {executionStats.networkRequests.map((req, index) => (
                                                    <div key={index} className="text-xs bg-zinc-50 dark:bg-zinc-900 p-3 rounded">
                                                        <div className="flex justify-between items-start mb-1">
                                                            <span className="font-medium text-zinc-700 dark:text-zinc-300">
                                                                {req.method} {req.url}
                                                            </span>
                                                            {req.status && (
                                                                <span
                                                                    className={`px-2 py-0.5 rounded text-xs ${
                                                                        req.status < 300
                                                                            ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                                                                            : 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
                                                                    }`}
                                                                >
                                                                    {req.status}
                                                                </span>
                                                            )}
                                                        </div>
                                                        <div className="flex gap-4 text-zinc-500">
                                                            <span>{req.duration}ms</span>
                                                            <span>{new Date(req.timestamp).toLocaleTimeString()}</span>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </CardContent>
                                    </Card>
                                </TabsContent>

                                {/* WebSocket Tab */}
                                <TabsContent value="websocket" className="space-y-4 mt-4">
                                    {/* Connection Status */}
                                    <Card>
                                        <CardHeader>
                                            <CardTitle className="text-sm flex items-center gap-2">
                                                <Wifi className="h-4 w-4" />
                                                连接状态
                                            </CardTitle>
                                        </CardHeader>
                                        <CardContent>
                                            <div className="space-y-2">
                                                <div className="flex items-center justify-between">
                                                    <span className="text-xs text-zinc-500">状态</span>
                                                    <span className={`text-xs font-medium px-2 py-1 rounded ${
                                                        connectionStatus === 'connected'
                                                            ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                                                            : connectionStatus === 'error'
                                                            ? 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
                                                            : 'bg-zinc-100 text-zinc-700 dark:bg-zinc-900 dark:text-zinc-300'
                                                    }`}>
                                                        {connectionStatus === 'connected' ? '已连接' :
                                                         connectionStatus === 'connecting' ? '连接中' :
                                                         connectionStatus === 'reconnecting' ? '重连中' :
                                                         connectionStatus === 'error' ? '错误' :
                                                         '已断开'}
                                                    </span>
                                                </div>
                                                <div className="flex items-center justify-between">
                                                    <span className="text-xs text-zinc-500">任务ID</span>
                                                    <span className="text-xs font-mono">{taskStatus?.task_id || 'N/A'}</span>
                                                </div>
                                                <div className="flex items-center justify-between">
                                                    <span className="text-xs text-zinc-500">消息数量</span>
                                                    <span className="text-xs font-medium">{websocketMessages.length}</span>
                                                </div>
                                            </div>
                                        </CardContent>
                                    </Card>

                                    {/* WebSocket Messages */}
                                    <Card>
                                        <CardHeader>
                                            <CardTitle className="text-sm">实时消息</CardTitle>
                                        </CardHeader>
                                        <CardContent>
                                            <div className="space-y-2 max-h-80 overflow-auto">
                                                {websocketMessages.length > 0 ? (
                                                    websocketMessages.slice().reverse().map((msg, index) => (
                                                        <div key={index} className="text-xs bg-zinc-50 dark:bg-zinc-900 p-3 rounded">
                                                            <div className="flex justify-between items-start mb-1">
                                                                <span className="font-medium text-blue-600 dark:text-blue-400">
                                                                    {msg.type}
                                                                </span>
                                                                <span className="text-zinc-500">
                                                                    {new Date(msg.timestamp).toLocaleTimeString()}
                                                                </span>
                                                            </div>
                                                            <pre className="text-zinc-700 dark:text-zinc-300 whitespace-pre-wrap overflow-x-auto">
                                                                {JSON.stringify(msg.data, null, 2)}
                                                            </pre>
                                                        </div>
                                                    ))
                                                ) : (
                                                    <div className="text-xs text-zinc-500 text-center py-4">
                                                        暂无WebSocket消息
                                                    </div>
                                                )}
                                            </div>
                                        </CardContent>
                                    </Card>
                                </TabsContent>

                                {/* Logs Tab */}
                                <TabsContent value="logs" className="space-y-4 mt-4">
                                    <Card>
                                        <CardHeader>
                                            <CardTitle className="text-sm">执行日志</CardTitle>
                                        </CardHeader>
                                        <CardContent>
                                            <div className="space-y-2 text-xs font-mono">
                                                {taskStatus ? (
                                                    <>
                                                        <div className="text-zinc-500">
                                                            [{new Date(taskStatus.created_at).toLocaleTimeString()}] 创建任务: {taskStatus.task_id}
                                                        </div>
                                                        <div className="text-zinc-500">
                                                            [{new Date(taskStatus.updated_at).toLocaleTimeString()}] 当前状态: {taskStatus.status}
                                                        </div>
                                                        <div className="text-blue-600 dark:text-blue-400">
                                                            [{new Date().toLocaleTimeString()}] 进度: {Math.round(taskStatus.progress_percentage)}%
                                                        </div>
                                                    </>
                                                ) : (
                                                    <div className="text-zinc-500">暂无日志</div>
                                                )}
                                            </div>
                                        </CardContent>
                                    </Card>
                                </TabsContent>
                            </Tabs>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
