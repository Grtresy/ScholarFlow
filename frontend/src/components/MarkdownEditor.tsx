'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Save, Undo, Redo, FileText } from 'lucide-react';
import { toast } from 'sonner';

interface MarkdownEditorProps {
    value: string;
    onChange: (value: string) => void;
    onSave?: () => void;
    readOnly?: boolean;
    autoSave?: boolean;
    autoSaveDelay?: number;
}

interface HistoryState {
    value: string;
    timestamp: number;
}

export function MarkdownEditor({
    value,
    onChange,
    onSave,
    readOnly = false,
    autoSave = true,
    autoSaveDelay = 500,
}: MarkdownEditorProps) {
    const [history, setHistory] = useState<HistoryState[]>([{ value, timestamp: Date.now() }]);
    const [historyIndex, setHistoryIndex] = useState(0);
    const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
    const [lastSaved, setLastSaved] = useState<Date | null>(null);

    // Update history when value changes externally
    useEffect(() => {
        if (value !== history[historyIndex]?.value) {
            setHistory(prev => [...prev.slice(0, historyIndex + 1), { value, timestamp: Date.now() }]);
            setHistoryIndex(prev => prev + 1);
            setHasUnsavedChanges(true);
        }
    }, [value]);

    // Auto-save functionality
    useEffect(() => {
        if (!autoSave || readOnly || !hasUnsavedChanges) return;

        const timer = setTimeout(() => {
            handleSave();
        }, autoSaveDelay);

        return () => clearTimeout(timer);
    }, [value, autoSave, autoSaveDelay, hasUnsavedChanges, readOnly]);

    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        const newValue = e.target.value;
        onChange(newValue);
        setHasUnsavedChanges(true);
    };

    const handleSave = useCallback(() => {
        if (onSave) {
            onSave();
            setHasUnsavedChanges(false);
            setLastSaved(new Date());
            toast.success('已保存');
        }
    }, [onSave]);

    const handleUndo = () => {
        if (historyIndex > 0) {
            const newIndex = historyIndex - 1;
            const prevValue = history[newIndex].value;
            setHistoryIndex(newIndex);
            onChange(prevValue);
            setHasUnsavedChanges(prevValue !== value);
        }
    };

    const handleRedo = () => {
        if (historyIndex < history.length - 1) {
            const newIndex = historyIndex + 1;
            const nextValue = history[newIndex].value;
            setHistoryIndex(newIndex);
            onChange(nextValue);
            setHasUnsavedChanges(nextValue !== value);
        }
    };

    const canUndo = historyIndex > 0;
    const canRedo = historyIndex < history.length - 1;

    return (
        <div className="flex flex-col h-full">
            {/* Toolbar */}
            <div className="flex items-center gap-2 p-2 border-b border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900">
                <div className="flex items-center gap-1">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleUndo}
                        disabled={!canUndo || readOnly}
                        title="撤销 (Ctrl+Z)"
                    >
                        <Undo className="h-4 w-4" />
                    </Button>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleRedo}
                        disabled={!canRedo || readOnly}
                        title="重做 (Ctrl+Y)"
                    >
                        <Redo className="h-4 w-4" />
                    </Button>
                </div>

                <div className="flex-1" />

                {hasUnsavedChanges && (
                    <span className="text-xs text-orange-600 dark:text-orange-400">
                        有未保存的更改
                    </span>
                )}

                {lastSaved && (
                    <span className="text-xs text-zinc-500">
                        上次保存: {lastSaved.toLocaleTimeString()}
                    </span>
                )}

                {onSave && (
                    <Button
                        variant="default"
                        size="sm"
                        onClick={handleSave}
                        disabled={!hasUnsavedChanges || readOnly}
                    >
                        <Save className="h-4 w-4 mr-1" />
                        保存
                    </Button>
                )}
            </div>

            {/* Editor */}
            <div className="flex-1 overflow-auto">
                <Textarea
                    value={value}
                    onChange={handleChange}
                    readOnly={readOnly}
                    placeholder="在此编辑 Markdown..."
                    className="h-full min-h-[500px] resize-none border-0 focus:ring-0 font-mono text-sm"
                    style={{
                        lineHeight: '1.6',
                    }}
                />
            </div>

            {/* Status bar */}
            <div className="flex items-center justify-between px-3 py-1 text-xs text-zinc-500 dark:text-zinc-400 border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-900">
                <div className="flex items-center gap-2">
                    <FileText className="h-3 w-3" />
                    <span>{value.length} 字符</span>
                    <span>•</span>
                    <span>{value.split(/\r?\n/).length} 行</span>
                </div>
                {autoSave && (
                    <div className="flex items-center gap-1">
                        <div className="h-2 w-2 rounded-full bg-green-500" />
                        <span>自动保存</span>
                    </div>
                )}
            </div>
        </div>
    );
}
