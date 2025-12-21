/**
 * WebSocket client for real-time workflow updates
 */

'use client';

import React, { useEffect, useState } from 'react';
import { TaskStatusResponse } from './api';

// ===== Type Definitions =====

export type ConnectionStatus = 'connecting' | 'connected' | 'reconnecting' | 'disconnected' | 'error';

export interface WebSocketMessage {
    type: string;
    data: any;
    timestamp: number;
}

export interface StatusUpdateData {
    task_id: string;
    status: string;
    progress: number;
    current_step: string;
    updated_fields?: string[];
}

export interface ChunkProgressData {
    task_id: string;
    chunk_index: number;
    total_chunks: number;
    completed_chunks: number;
    current_chunk_content?: string;
}

export interface RenderProgressData {
    task_id: string;
    stage: string;
    percentage: number;
    output_format: string;
}

export interface ReviewRequiredData {
    task_id: string;
    review_points: any[];
    can_edit: boolean;
}

export interface ErrorData {
    task_id: string;
    error_code: string;
    error_message: string;
    node_name?: string;
    recovery_hint?: string;
}

export interface CompletedData {
    task_id: string;
    result_url?: string;
    output_format: string;
}

// ===== WebSocket Client Class =====

export class WorkflowWebSocketClient {
    private ws: WebSocket | null = null;
    private taskId: string;
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private reconnectDelay = 1000; // Start with 1 second
    private maxReconnectDelay = 30000; // Max 30 seconds
    private heartbeatInterval: NodeJS.Timeout | null = null;
    private messageQueue: WebSocketMessage[] = [];
    private listeners: Map<string, Set<(data: any) => void>> = new Map();
    private connectionStatus: ConnectionStatus = 'disconnected';
    private fallbackPolling: NodeJS.Timeout | null = null;
    private onStatusChangeCallbacks: ((status: ConnectionStatus) => void)[] = [];

    constructor(taskId: string) {
        this.taskId = taskId;
    }

    // ===== Connection Management =====

    async connect(): Promise<void> {
        if (this.ws?.readyState === WebSocket.OPEN) {
            console.log('[WebSocket] Already connected');
            return;
        }

        this.updateConnectionStatus('connecting');

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.hostname || 'localhost'; // Fallback to localhost if hostname is empty
        const port = 8000;
        const wsUrl = `${protocol}//${host}:${port}/ws/${this.taskId}`;

        console.log('[WebSocket] Connecting to:', wsUrl);
        console.log('[WebSocket] Protocol:', protocol, 'Host:', host, 'Port:', port);
        console.log('[WebSocket] Current page:', window.location.href);

        // Check if WebSocket is supported
        if (typeof WebSocket === 'undefined') {
            console.warn('[WebSocket] WebSocket not supported, using fallback polling');
            this.updateConnectionStatus('error');
            this.startFallbackPolling();
            return;
        }

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = this.handleOpen.bind(this);
            this.ws.onmessage = this.handleMessage.bind(this);
            this.ws.onclose = this.handleClose.bind(this);
            this.ws.onerror = this.handleError.bind(this);

            // Set connection timeout
            setTimeout(() => {
                if (this.connectionStatus === 'connecting') {
                    console.warn('[WebSocket] Connection timeout after 10s');
                    this.updateConnectionStatus('error');
                    this.scheduleReconnect();
                }
            }, 10000);
        } catch (error) {
            console.warn('[WebSocket] Connection error:', error);
            this.updateConnectionStatus('error');
            this.scheduleReconnect();
        }
    }

    private handleOpen(): void {
        console.log('[WebSocket] Connected successfully');
        this.reconnectAttempts = 0;
        this.reconnectDelay = 1000;
        this.updateConnectionStatus('connected');

        // Send initial auth message
        this.send({
            type: 'auth',
            data: { task_id: this.taskId },
            timestamp: Date.now()
        });

        // Start heartbeat
        this.startHeartbeat();

        // Process queued messages
        this.processMessageQueue();

        // Stop fallback polling if exists
        if (this.fallbackPolling) {
            clearInterval(this.fallbackPolling);
            this.fallbackPolling = null;
        }
    }

    private handleMessage(event: MessageEvent): void {
        try {
            const message: WebSocketMessage = JSON.parse(event.data);
            console.log('[WebSocket] Received message:', message.type);

            // Handle heartbeat
            if (message.type === 'pong') {
                return;
            }

            // Emit to listeners
            this.emit(message.type, message.data);

            // Emit general message event
            this.emit('message', message);
        } catch (error) {
            console.error('[WebSocket] Error parsing message:', error);
        }
    }

    private handleClose(event: CloseEvent): void {
        console.log('[WebSocket] Connection closed:', event.code, event.reason);
        this.updateConnectionStatus('disconnected');
        this.stopHeartbeat();

        // If it was a normal closure or max reconnection attempts reached, use fallback polling
        if (event.code === 1000 || this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('[WebSocket] Using fallback polling instead of WebSocket');
            this.startFallbackPolling();
        } else {
            // Try to reconnect
            this.updateConnectionStatus('reconnecting');
            this.scheduleReconnect();
        }
    }

    private handleError(error: Event): void {
        // WebSocket onerror events typically have very limited information
        // Don't log the raw error object as it's usually empty or unhelpful
        const errorMessage = this.extractErrorMessage(error);

        // Log a concise, helpful error message instead of the raw event
        console.warn('[WebSocket] Connection failed, will retry or use fallback polling');

        this.updateConnectionStatus('error');

        // Start fallback polling when WebSocket fails
        console.log('[WebSocket] Switching to fallback polling for task:', this.taskId);
        this.startFallbackPolling();
    }

    private extractErrorMessage(error: Event): string {
        // WebSocket error events in browsers typically don't contain useful details
        // Return a generic, user-friendly message instead
        if (error instanceof ErrorEvent) {
            return error.message || 'Connection failed';
        }

        // For Event objects from WebSocket, we can't get much detail
        // The connection state (connecting -> error) tells us what we need to know
        return 'WebSocket connection failed';
    }

    private scheduleReconnect(): void {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('[WebSocket] Max reconnection attempts reached');
            this.updateConnectionStatus('error');
            this.startFallbackPolling();
            return;
        }

        const delay = this.reconnectDelay;
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
        this.reconnectAttempts++;

        console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

        setTimeout(() => {
            this.connect();
        }, delay);
    }

    // ===== Heartbeat =====

    private startHeartbeat(): void {
        this.heartbeatInterval = setInterval(() => {
            this.send({
                type: 'ping',
                data: { timestamp: Date.now() },
                timestamp: Date.now()
            });
        }, 30000); // Send ping every 30 seconds
    }

    private stopHeartbeat(): void {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }

    // ===== Fallback Polling =====

    private startFallbackPolling(): void {
        console.log('[WebSocket] Starting fallback polling');
        let consecutiveErrors = 0;
        const maxConsecutiveErrors = 3;

        this.fallbackPolling = setInterval(async () => {
            try {
                // Use the regular API as fallback
                const response = await fetch(`/api/tasks/${this.taskId}/status`);
                if (response.ok) {
                    const data = await response.json();
                    consecutiveErrors = 0; // Reset error counter on success
                    this.emit('status_update', data);
                } else if (response.status === 404) {
                    // Task not found - stop polling and emit error
                    console.log('[WebSocket] Task not found (404), stopping fallback polling');
                    this.stopHeartbeat();
                    if (this.fallbackPolling) {
                        clearInterval(this.fallbackPolling);
                        this.fallbackPolling = null;
                    }
                    this.emit('error', {
                        task_id: this.taskId,
                        error_code: 'TASK_NOT_FOUND',
                        error_message: `任务 ${this.taskId} 不存在或已被删除`,
                        details: '请检查任务ID是否正确，或返回首页创建新任务'
                    });
                } else {
                    consecutiveErrors++;
                    console.log(`[WebSocket] API error (${response.status}), consecutive errors: ${consecutiveErrors}`);

                    if (consecutiveErrors >= maxConsecutiveErrors) {
                        console.log('[WebSocket] Max consecutive errors reached, stopping fallback polling');
                        this.stopHeartbeat();
                        if (this.fallbackPolling) {
                            clearInterval(this.fallbackPolling);
                            this.fallbackPolling = null;
                        }
                        this.emit('error', {
                            task_id: this.taskId,
                            error_code: 'API_ERROR',
                            error_message: `API返回错误 (${response.status})`,
                            details: '请稍后重试或联系管理员'
                        });
                    }
                }
            } catch (error) {
                consecutiveErrors++;
                console.error('[WebSocket] Fallback polling error:', error);

                if (consecutiveErrors >= maxConsecutiveErrors) {
                    console.log('[WebSocket] Max consecutive errors reached, stopping fallback polling');
                    this.stopHeartbeat();
                    if (this.fallbackPolling) {
                        clearInterval(this.fallbackPolling);
                        this.fallbackPolling = null;
                    }
                    this.emit('error', {
                        task_id: this.taskId,
                        error_code: 'NETWORK_ERROR',
                        error_message: '网络连接错误',
                        details: '请检查网络连接或稍后重试'
                    });
                }
            }
        }, 2000); // Poll every 2 seconds
    }

    // ===== Message Handling =====

    private send(message: WebSocketMessage): void {
        if (this.ws?.readyState === WebSocket.OPEN) {
            try {
                this.ws.send(JSON.stringify(message));
            } catch (error) {
                console.error('[WebSocket] Error sending message:', error);
                // Queue message for later
                this.messageQueue.push(message);
            }
        } else {
            // Queue message for when connection is restored
            this.messageQueue.push(message);
        }
    }

    private processMessageQueue(): void {
        while (this.messageQueue.length > 0) {
            const message = this.messageQueue.shift();
            if (message) {
                try {
                    this.ws?.send(JSON.stringify(message));
                } catch (error) {
                    console.error('[WebSocket] Error sending queued message:', error);
                }
            }
        }
    }

    // ===== Event Listeners =====

    on(type: string, callback: (data: any) => void): void {
        if (!this.listeners.has(type)) {
            this.listeners.set(type, new Set());
        }
        this.listeners.get(type)!.add(callback);
    }

    off(type: string, callback: (data: any) => void): void {
        const callbacks = this.listeners.get(type);
        if (callbacks) {
            callbacks.delete(callback);
        }
    }

    private emit(type: string, data: any): void {
        const callbacks = this.listeners.get(type);
        if (callbacks) {
            callbacks.forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`[WebSocket] Error in ${type} callback:`, error);
                }
            });
        }
    }

    onStatusChange(callback: (status: ConnectionStatus) => void): void {
        this.onStatusChangeCallbacks.push(callback);
    }

    private updateConnectionStatus(status: ConnectionStatus): void {
        this.connectionStatus = status;
        this.onStatusChangeCallbacks.forEach(callback => {
            try {
                callback(status);
            } catch (error) {
                console.error('[WebSocket] Error in status change callback:', error);
            }
        });
    }

    // ===== Public Methods =====

    getStatus(): ConnectionStatus {
        return this.connectionStatus;
    }

    disconnect(): void {
        console.log('[WebSocket] Disconnecting');
        this.stopHeartbeat();

        if (this.fallbackPolling) {
            clearInterval(this.fallbackPolling);
            this.fallbackPolling = null;
        }

        if (this.ws) {
            this.ws.close(1000, 'Client disconnect');
            this.ws = null;
        }

        this.updateConnectionStatus('disconnected');
    }

    // ===== Convenience Methods for Common Events =====

    onStatusUpdate(callback: (data: StatusUpdateData) => void): void {
        this.on('status_update', callback);
    }

    onChunkProgress(callback: (data: ChunkProgressData) => void): void {
        this.on('chunk_progress', callback);
    }

    onRenderProgress(callback: (data: RenderProgressData) => void): void {
        this.on('render_progress', callback);
    }

    onReviewRequired(callback: (data: ReviewRequiredData) => void): void {
        this.on('review_required', callback);
    }

    onError(callback: (data: ErrorData) => void): void {
        this.on('error', callback);
    }

    onCompleted(callback: (data: CompletedData) => void): void {
        this.on('completed', callback);
    }

    onConnected(callback: (data: any) => void): void {
        this.on('connected', callback);
    }
}

// ===== Hook for React Components =====

export function useWorkflowWebSocket(taskId: string | null) {
    const [client, setClient] = React.useState<WorkflowWebSocketClient | null>(null);
    const [connectionStatus, setConnectionStatus] = React.useState<ConnectionStatus>('disconnected');

    React.useEffect(() => {
        if (!taskId) {
            return;
        }

        const wsClient = new WorkflowWebSocketClient(taskId);

        wsClient.onStatusChange((status) => {
            console.log('[WebSocket] Status changed:', status);
            setConnectionStatus(status);
        });

        setClient(wsClient);
        wsClient.connect();

        return () => {
            console.log('[WebSocket] Cleaning up client');
            wsClient.disconnect();
        };
    }, [taskId]);

    return { client, connectionStatus };
}

// ===== React hook for task status with WebSocket =====

export function useTaskStatusWebSocket(
    taskId: string | null,
    onReviewRequired?: (status: TaskStatusResponse) => void,
    onCompleted?: (status: TaskStatusResponse) => void,
    onError?: (error: string) => void
) {
    const [status, setStatus] = React.useState<TaskStatusResponse | null>(null);
    const [error, setError] = React.useState<string | null>(null);
    const [connectionStatus, setConnectionStatus] = React.useState<ConnectionStatus>('disconnected');

    React.useEffect(() => {
        if (!taskId) {
            return;
        }

        const wsClient = new WorkflowWebSocketClient(taskId);

        // Status change handler
        wsClient.onStatusChange((status) => {
            console.log('[WebSocket] Connection status:', status);
            setConnectionStatus(status);
        });

        // Status update handler
        wsClient.onStatusUpdate((data) => {
            console.log('[WebSocket] Status update:', data.status);
            setStatus({
                task_id: data.task_id,
                status: data.status,
                progress_percentage: data.progress,
                current_step: data.current_step,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
                needs_human_review: false,
                review_points: []
            });
            setError(null);
        });

        // Review required handler
        wsClient.onReviewRequired((data) => {
            console.log('[WebSocket] Review required');
            if (onReviewRequired) {
                onReviewRequired({
                    task_id: data.task_id,
                    status: 'human_review',
                    progress_percentage: 50,
                    current_step: 'Waiting for review',
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                    needs_human_review: true,
                    review_points: data.review_points
                });
            }
        });

        // Error handler
        wsClient.onError((data) => {
            console.error('[WebSocket] Error:', data.error_message);
            setError(data.error_message);
            if (onError) {
                onError(data.error_message);
            }
        });

        // Completed handler
        wsClient.onCompleted((data) => {
            console.log('[WebSocket] Task completed');
            if (onCompleted && status) {
                onCompleted(status);
            }
        });

        // Connect
        wsClient.connect();

        return () => {
            console.log('[WebSocket] Cleaning up task status client');
            wsClient.disconnect();
        };
    }, [taskId, onReviewRequired, onCompleted, onError, status]);

    // Initial fetch: Get current status immediately
    React.useEffect(() => {
        if (!taskId) {
            return;
        }

        // Import getTaskStatus dynamically to avoid SSR issues
        import('@/lib/api').then(({ getTaskStatus }) => {
            getTaskStatus(taskId)
                .then((data) => {
                    console.log('[WebSocket] Initial status fetched:', data.status);
                    setStatus(data);
                    setError(null);

                    // Check if needs review and trigger callback
                    if (data.needs_human_review && onReviewRequired) {
                        onReviewRequired(data);
                    }
                    // Check if completed and trigger callback
                    else if (data.status === 'completed' && onCompleted) {
                        onCompleted(data);
                    }
                })
                .catch((err) => {
                    console.error('[WebSocket] Failed to fetch initial status:', err);
                    setError(err.message || 'Failed to fetch task status');
                    if (onError) {
                        onError(err.message || 'Failed to fetch task status');
                    }
                });
        });
    }, [taskId, onReviewRequired, onCompleted, onError]);

    return { status, error, connectionStatus };
}
