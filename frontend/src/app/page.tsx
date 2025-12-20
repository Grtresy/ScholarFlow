'use client';

import React, { useState, useEffect } from 'react';
import { UploadSection } from '@/components/UploadSection';
import { TaskStatus } from '@/components/TaskStatus';
import { ReviewSection } from '@/components/ReviewSection';
import { ResultSection } from '@/components/ResultSection';
import { DebugPanel } from '@/components/DebugPanel';
import { Button } from '@/components/ui/button';
import { TaskStatusResponse } from '@/lib/api';
import { Toaster } from '@/components/ui/sonner';
import { Bug } from 'lucide-react';

export default function Home() {
    const [taskId, setTaskId] = useState<string | null>(null);
    const [currentStatus, setCurrentStatus] = useState<TaskStatusResponse | null>(null);
    const [view, setView] = useState<'upload' | 'processing' | 'review' | 'result'>('upload');
    const [pollingKey, setPollingKey] = useState(0); // Increment to restart polling
    const [showDebug, setShowDebug] = useState(false);

    console.log('[DEBUG] Current view:', view, 'taskId:', taskId, 'pollingKey:', pollingKey);

    // Keyboard shortcut for debug panel (Ctrl+D or Cmd+D)
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
                e.preventDefault();
                setShowDebug(prev => !prev);
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, []);

    const handleTaskCreated = (id: string) => {
        console.log('[DEBUG] handleTaskCreated called with id:', id);
        setTaskId(id);
        setView('processing');
    };

    const handleReviewRequired = (status: TaskStatusResponse) => {
        console.log('[DEBUG] handleReviewRequired called');
        setCurrentStatus(status);
        setView('review');
    };

    const handleReviewed = () => {
        console.log('[DEBUG] handleReviewed called, switching to processing');
        setView('processing');
        setPollingKey(prev => prev + 1); // Restart polling after feedback
    };

    const handleCompleted = (status: TaskStatusResponse) => {
        console.log('[DEBUG] handleCompleted called');
        setCurrentStatus(status);
        setView('result');
    };

    return (
        <main className="min-h-screen bg-zinc-50 dark:bg-zinc-950 py-12 px-4">
            <div className="max-w-5xl mx-auto space-y-8">
                <header className="text-center space-y-2 relative">
                    <h1 className="text-4xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
                        ScholarFlow
                    </h1>
                    <p className="text-zinc-500 dark:text-zinc-400">
                        智能学术论文演示文稿生成系统
                    </p>
                    {/* Debug button */}
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowDebug(!showDebug)}
                        className="absolute top-0 right-0 text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200"
                        title="调试面板 (Ctrl+D)"
                    >
                        <Bug className="h-4 w-4" />
                    </Button>
                </header>

                <div className="transition-all duration-500 ease-in-out">
                    {view === 'upload' && (
                        <UploadSection onTaskCreated={handleTaskCreated} />
                    )}

                    {view === 'processing' && taskId && (
                        <div className="max-w-2xl mx-auto">
                            <TaskStatus
                                taskId={taskId}
                                onReviewRequired={handleReviewRequired}
                                onCompleted={handleCompleted}
                                restartPolling={pollingKey}
                            />
                        </div>
                    )}

                    {view === 'review' && currentStatus && (
                        <ReviewSection
                            taskStatus={currentStatus}
                            onReviewed={handleReviewed}
                        />
                    )}

                    {view === 'result' && currentStatus && (
                        <ResultSection taskStatus={currentStatus} />
                    )}
                </div>
            </div>
            <Toaster position="top-center" />

            {/* Debug Panel */}
            <DebugPanel
                isOpen={showDebug}
                onToggle={() => setShowDebug(!showDebug)}
                taskStatus={currentStatus}
            />
        </main>
    );
}
