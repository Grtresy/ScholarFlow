'use client';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { RefreshCw, ExternalLink, Download } from 'lucide-react';
import { toast } from 'sonner';
import { renderPreview as callRenderPreview } from '@/lib/api';

interface MarpPreviewProps {
    markdown: string;
    className?: string;
    onRefresh?: () => void;
}

export function MarpPreview({ markdown, className = '', onRefresh }: MarpPreviewProps) {
    const [htmlContent, setHtmlContent] = useState<string>('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const renderPreview = async () => {
        setLoading(true);
        setError(null);

        try {
            // Call the backend render endpoint via API
            const data = await callRenderPreview(markdown);
            setHtmlContent(data.html);
        } catch (err) {
            console.error('Render error:', err);
            setError(err instanceof Error ? err.message : '渲染失败');
            toast.error('预览渲染失败');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        // Debounce the preview rendering
        const timer = setTimeout(() => {
            if (markdown.trim()) {
                renderPreview();
            }
        }, 500);

        return () => clearTimeout(timer);
    }, [markdown]);

    const handleRefresh = () => {
        if (onRefresh) {
            onRefresh();
        } else {
            renderPreview();
        }
    };

    const handleOpenInNewTab = () => {
        if (htmlContent) {
            const newWindow = window.open('', '_blank');
            if (newWindow) {
                newWindow.document.write(htmlContent);
                newWindow.document.close();
            }
        }
    };

    return (
        <div className={`flex flex-col h-full ${className}`}>
            {/* Toolbar */}
            <div className="flex items-center gap-2 p-2 border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900">
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleRefresh}
                    disabled={loading}
                >
                    <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
                    刷新
                </Button>

                <div className="flex-1" />

                <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleOpenInNewTab}
                    disabled={!htmlContent}
                >
                    <ExternalLink className="h-4 w-4 mr-1" />
                    新标签页打开
                </Button>

                <Button
                    variant="ghost"
                    size="sm"
                    disabled
                >
                    <Download className="h-4 w-4 mr-1" />
                    下载
                </Button>
            </div>

            {/* Preview content */}
            <div className="flex-1 overflow-auto bg-white dark:bg-zinc-950">
                {loading && (
                    <div className="flex items-center justify-center h-full">
                        <div className="text-center">
                            <RefreshCw className="h-8 w-8 animate-spin mx-auto text-blue-500 mb-2" />
                            <p className="text-sm text-zinc-500">渲染中...</p>
                        </div>
                    </div>
                )}

                {error && (
                    <div className="flex items-center justify-center h-full p-4">
                        <div className="text-center">
                            <p className="text-red-600 dark:text-red-400 mb-2">渲染失败</p>
                            <p className="text-xs text-zinc-500">{error}</p>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={handleRefresh}
                                className="mt-2"
                            >
                                重试
                            </Button>
                        </div>
                    </div>
                )}

                {!loading && !error && htmlContent && (
                    <iframe
                        srcDoc={htmlContent}
                        className="w-full h-full border-0"
                        title="Marp Preview"
                        sandbox="allow-same-origin"
                    />
                )}

                {!loading && !error && !htmlContent && (
                    <div className="flex items-center justify-center h-full">
                        <div className="text-center text-zinc-500">
                            <p>暂无内容</p>
                        </div>
                    </div>
                )}
            </div>

            {/* Status bar */}
            <div className="flex items-center justify-between px-3 py-1 text-xs text-zinc-500 dark:text-zinc-400 border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900">
                <span>Marp 预览</span>
                {htmlContent && !loading && (
                    <span>已渲染</span>
                )}
            </div>
        </div>
    );
}
