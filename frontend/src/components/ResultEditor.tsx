'use client';

import React, { useState, useEffect } from 'react';
import { MarkdownEditor } from '@/components/MarkdownEditor';
import { MarpPreview } from '@/components/MarpPreview';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Download, Edit3, Eye } from 'lucide-react';
import { getMarkdownContent, saveMarkdownContent, downloadPresentation, triggerDownload } from '@/lib/api';
import { toast } from 'sonner';

interface ResultEditorProps {
    taskId: string;
    initialMarkdown: string;
    onSave?: (markdown: string) => void;
}

export function ResultEditor({ taskId, initialMarkdown, onSave }: ResultEditorProps) {
    const [markdown, setMarkdown] = useState(initialMarkdown);
    const [viewMode, setViewMode] = useState<'split' | 'editor' | 'preview'>('split');
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        setMarkdown(initialMarkdown);
    }, [initialMarkdown]);

    const handleSave = async () => {
        setSaving(true);
        try {
            await saveMarkdownContent(taskId, markdown, 'marp_markdown');
            if (onSave) {
                onSave(markdown);
            }
            toast.success('保存成功');
        } catch (error) {
            console.error('Save error:', error);
            toast.error('保存失败');
        } finally {
            setSaving(false);
        }
    };

    const handleDownload = async () => {
        try {
            toast.info('正在下载...');
            const blob = await downloadPresentation(taskId);

            const timestamp = new Date().toISOString().split('T')[0];
            const filename = `presentation_${taskId}_${timestamp}.pptx`;

            triggerDownload(blob, filename);
            toast.success('下载成功！');
        } catch (error) {
            console.error('Download error:', error);
            toast.error(error instanceof Error ? error.message : '下载失败，请重试');
        }
    };

    return (
        <div className="h-[800px] flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950">
                <div className="flex items-center gap-2">
                    <Button
                        variant={viewMode === 'split' ? 'default' : 'ghost'}
                        size="sm"
                        onClick={() => setViewMode('split')}
                    >
                        分割视图
                    </Button>
                    <Button
                        variant={viewMode === 'editor' ? 'default' : 'ghost'}
                        size="sm"
                        onClick={() => setViewMode('editor')}
                    >
                        <Edit3 className="h-3 w-3 mr-1" />
                        仅编辑
                    </Button>
                    <Button
                        variant={viewMode === 'preview' ? 'default' : 'ghost'}
                        size="sm"
                        onClick={() => setViewMode('preview')}
                    >
                        <Eye className="h-3 w-3 mr-1" />
                        仅预览
                    </Button>
                </div>

                <div className="flex items-center gap-2">
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={handleDownload}
                    >
                        <Download className="h-4 w-4 mr-1" />
                        下载 PPT
                    </Button>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-hidden">
                {viewMode === 'split' && (
                    <div className="grid grid-cols-2 h-full divide-x divide-zinc-200 dark:divide-zinc-800">
                        <div className="h-full">
                            <MarkdownEditor
                                value={markdown}
                                onChange={setMarkdown}
                                onSave={handleSave}
                                autoSave={true}
                                autoSaveDelay={1000}
                            />
                        </div>
                        <div className="h-full">
                            <MarpPreview markdown={markdown} />
                        </div>
                    </div>
                )}

                {viewMode === 'editor' && (
                    <div className="h-full">
                        <MarkdownEditor
                            value={markdown}
                            onChange={setMarkdown}
                            onSave={handleSave}
                            autoSave={true}
                            autoSaveDelay={1000}
                        />
                    </div>
                )}

                {viewMode === 'preview' && (
                    <div className="h-full">
                        <MarpPreview markdown={markdown} />
                    </div>
                )}
            </div>

            {/* Status bar */}
            <div className="flex items-center justify-between px-4 py-2 text-xs text-zinc-500 dark:text-zinc-400 border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900">
                <div className="flex items-center gap-4">
                    <span>任务 ID: {taskId}</span>
                    <span>•</span>
                    <span>{markdown.length} 字符</span>
                </div>
                {saving && (
                    <span className="text-blue-600 dark:text-blue-400">保存中...</span>
                )}
            </div>
        </div>
    );
}
