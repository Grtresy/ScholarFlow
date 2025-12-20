'use client';

import React, { useState, useCallback } from 'react';
import { uploadPDF, createTask, getPromptTemplates } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { Textarea } from '@/components/ui/textarea';
import { Settings2, ChevronDown, ChevronUp, FileText, Edit3, Palette } from 'lucide-react';
import { toast } from 'sonner';

interface UploadSectionProps {
    onTaskCreated: (taskId: string) => void;
}

type StyleMode = 'preset' | 'custom';

interface StyleConfig {
    mode: StyleMode;
    presetStyle?: 'academic' | 'popular' | 'business';
    customStage1Prompt?: string;
    customStage2Prompt?: string;
}

export function UploadSection({ onTaskCreated }: UploadSectionProps) {
    const [file, setFile] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);
    const [dragActive, setDragActive] = useState(false);
    const [showAdvanced, setShowAdvanced] = useState(false);

    // Task parameters
    const [maxChars, setMaxChars] = useState(6000);
    const [targetChunks, setTargetChunks] = useState(6);
    const [outputFormat, setOutputFormat] = useState('pptx');
    const [enableHumanReview, setEnableHumanReview] = useState(true);

    // Unified style and prompt configuration
    const [styleConfig, setStyleConfig] = useState<StyleConfig>({
        mode: 'preset',
        presetStyle: 'academic',
    });

    const handleDrag = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true);
        } else if (e.type === 'dragleave') {
            setDragActive(false);
        }
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);

        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            const droppedFile = e.dataTransfer.files[0];
            if (droppedFile.type === 'application/pdf') {
                setFile(droppedFile);
            } else {
                toast.error('请上传 PDF 文件');
            }
        }
    }, []);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            const selectedFile = e.target.files[0];
            if (selectedFile.type === 'application/pdf') {
                setFile(selectedFile);
            } else {
                toast.error('请上传 PDF 文件');
            }
        }
    };

    const handleUpload = async () => {
        if (!file) {
            toast.error('请先选择文件');
            return;
        }

        setUploading(true);
        try {
            // Step 1: Upload PDF
            toast.info('正在上传文件...');
            const uploadResponse = await uploadPDF(file);

            // Step 2: Create task with unified style configuration
            toast.info('正在创建任务...');

            const taskData: any = {
                pdf_path: uploadResponse.pdf_path,
                max_chars: maxChars,
                target_chunks: targetChunks,
                output_format: outputFormat,
                enable_human_review: enableHumanReview,
            };

            // Add style and prompt configuration
            if (styleConfig.mode === 'preset') {
                taskData.presentation_style = styleConfig.presetStyle;
            } else {
                // Custom mode
                taskData.presentation_style = 'custom';
                if (styleConfig.customStage1Prompt?.trim()) {
                    taskData.custom_stage1_prompt = styleConfig.customStage1Prompt;
                }
                if (styleConfig.customStage2Prompt?.trim()) {
                    taskData.custom_stage2_prompt = styleConfig.customStage2Prompt;
                }
            }

            const taskResponse = await createTask(taskData);

            toast.success('任务创建成功！');
            onTaskCreated(taskResponse.task_id);
        } catch (error) {
            console.error('Upload error:', error);
            toast.error(error instanceof Error ? error.message : '上传失败，请重试');
        } finally {
            setUploading(false);
        }
    };

    return (
        <Card className="w-full max-w-2xl mx-auto">
            <CardHeader>
                <CardTitle>上传学术论文</CardTitle>
                <CardDescription>
                    上传 PDF 格式的学术论文，系统将自动生成演示文稿
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* Drag and drop area */}
                <div
                    className={`
            relative border-2 border-dashed rounded-lg p-12 text-center transition-colors
            ${dragActive ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/20' : 'border-zinc-300 dark:border-zinc-700'}
            ${file ? 'bg-zinc-50 dark:bg-zinc-900' : ''}
          `}
                    onDragEnter={handleDrag}
                    onDragLeave={handleDrag}
                    onDragOver={handleDrag}
                    onDrop={handleDrop}
                >
                    <input
                        type="file"
                        accept="application/pdf"
                        onChange={handleFileChange}
                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                        disabled={uploading}
                    />

                    <div className="space-y-2">
                        {file ? (
                            <>
                                <svg
                                    className="mx-auto h-12 w-12 text-green-500"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                                    />
                                </svg>
                                <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">
                                    {file.name}
                                </p>
                                <p className="text-xs text-zinc-500 dark:text-zinc-400">
                                    {(file.size / 1024 / 1024).toFixed(2)} MB
                                </p>
                            </>
                        ) : (
                            <>
                                <svg
                                    className="mx-auto h-12 w-12 text-zinc-400"
                                    stroke="currentColor"
                                    fill="none"
                                    viewBox="0 0 48 48"
                                >
                                    <path
                                        d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                                        strokeWidth={2}
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                    />
                                </svg>
                                <p className="text-sm text-zinc-600 dark:text-zinc-400">
                                    <span className="font-semibold">点击上传</span> 或拖拽文件到此处
                                </p>
                                <p className="text-xs text-zinc-500 dark:text-zinc-500">
                                    仅支持 PDF 格式
                                </p>
                            </>
                        )}
                    </div>
                </div>

                {/* Unified Style and Prompt Configuration */}
                <div className="border rounded-lg overflow-hidden border-zinc-200 dark:border-zinc-800">
                    <button
                        type="button"
                        onClick={() => setShowAdvanced(!showAdvanced)}
                        className="w-full flex items-center justify-between p-3 bg-zinc-50 dark:bg-zinc-900/50 hover:bg-zinc-100 dark:hover:bg-zinc-900 transition-colors"
                    >
                        <div className="flex items-center gap-2 text-sm font-medium">
                            <Palette className="h-4 w-4" />
                            <span>风格与提示词配置</span>
                        </div>
                        {showAdvanced ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </button>

                    {showAdvanced && (
                        <div className="p-4 space-y-4 animate-in fade-in slide-in-from-top-2 duration-200">
                            {/* Step 1: Choose Style Mode */}
                            <div className="space-y-3">
                                <Label>选择演示风格</Label>
                                <div className="grid grid-cols-2 gap-3">
                                    <button
                                        type="button"
                                        onClick={() => setStyleConfig({ mode: 'preset', presetStyle: 'academic' })}
                                        className={`p-3 rounded-lg border text-left transition-colors ${
                                            styleConfig.mode === 'preset' && styleConfig.presetStyle === 'academic'
                                                ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/20'
                                                : 'border-zinc-200 dark:border-zinc-700 hover:border-zinc-300'
                                        }`}
                                    >
                                        <div className="font-medium">学术风格</div>
                                        <div className="text-xs text-zinc-500 mt-1">
                                            学术会议、论文答辩、正式汇报
                                        </div>
                                    </button>

                                    <button
                                        type="button"
                                        onClick={() => setStyleConfig({ mode: 'preset', presetStyle: 'popular' })}
                                        className={`p-3 rounded-lg border text-left transition-colors ${
                                            styleConfig.mode === 'preset' && styleConfig.presetStyle === 'popular'
                                                ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/20'
                                                : 'border-zinc-200 dark:border-zinc-700 hover:border-zinc-300'
                                        }`}
                                    >
                                        <div className="font-medium">科普风格</div>
                                        <div className="text-xs text-zinc-500 mt-1">
                                            向非专业人士介绍、通俗易懂
                                        </div>
                                    </button>

                                    <button
                                        type="button"
                                        onClick={() => setStyleConfig({ mode: 'preset', presetStyle: 'business' })}
                                        className={`p-3 rounded-lg border text-left transition-colors ${
                                            styleConfig.mode === 'preset' && styleConfig.presetStyle === 'business'
                                                ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/20'
                                                : 'border-zinc-200 dark:border-zinc-700 hover:border-zinc-300'
                                        }`}
                                    >
                                        <div className="font-medium">商务风格</div>
                                        <div className="text-xs text-zinc-500 mt-1">
                                            向投资人、客户展示商业价值
                                        </div>
                                    </button>

                                    <button
                                        type="button"
                                        onClick={() => setStyleConfig({ mode: 'custom' })}
                                        className={`p-3 rounded-lg border text-left transition-colors ${
                                            styleConfig.mode === 'custom'
                                                ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/20'
                                                : 'border-zinc-200 dark:border-zinc-700 hover:border-zinc-300'
                                        }`}
                                    >
                                        <div className="font-medium">自定义风格</div>
                                        <div className="text-xs text-zinc-500 mt-1">
                                            有经验的用户，完全自定义
                                        </div>
                                    </button>
                                </div>
                            </div>

                            {/* Step 2: Configuration Details based on selection */}
                            {styleConfig.mode === 'preset' ? (
                                <div className="p-3 bg-green-50 dark:bg-green-950/20 rounded-lg">
                                    <div className="flex items-center gap-2 text-sm text-green-700 dark:text-green-300">
                                        <FileText className="h-4 w-4" />
                                        <span>将使用 {styleConfig.presetStyle} 风格的默认提示词</span>
                                    </div>
                                </div>
                            ) : (
                                <div className="space-y-4">
                                    <Separator />
                                    <div className="space-y-3">
                                        <Label>Stage 1 提示词（大纲生成）</Label>
                                        <Textarea
                                            value={styleConfig.customStage1Prompt || ''}
                                            onChange={(e) =>
                                                setStyleConfig({
                                                    ...styleConfig,
                                                    customStage1Prompt: e.target.value,
                                                })
                                            }
                                            placeholder="输入自定义的 Stage 1 提示词（用于生成PPT大纲）"
                                            className="min-h-[120px] font-mono text-sm"
                                        />
                                        <p className="text-[10px] text-zinc-500">
                                            💡 可用变量：&#123;content&#125;（论文内容）
                                        </p>
                                    </div>

                                    <div className="space-y-3">
                                        <Label>Stage 2 提示词（渲染生成）</Label>
                                        <Textarea
                                            value={styleConfig.customStage2Prompt || ''}
                                            onChange={(e) =>
                                                setStyleConfig({
                                                    ...styleConfig,
                                                    customStage2Prompt: e.target.value,
                                                })
                                            }
                                            placeholder="输入自定义的 Stage 2 提示词（用于生成Marp Markdown）"
                                            className="min-h-[120px] font-mono text-sm"
                                        />
                                        <p className="text-[10px] text-zinc-500">
                                            💡 可用变量：&#123;outline&#125;（合并后的大纲）
                                        </p>
                                    </div>
                                </div>
                            )}

                            <Separator />

                            {/* Other parameters */}
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="format">输出格式</Label>
                                    <Select value={outputFormat} onValueChange={setOutputFormat}>
                                        <SelectTrigger id="format">
                                            <SelectValue placeholder="选择格式" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="pptx">PowerPoint (.pptx)</SelectItem>
                                            <SelectItem value="pdf">PDF Document (.pdf)</SelectItem>
                                            <SelectItem value="html">HTML Presentation (.html)</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="maxChars">最大字符数 (每页)</Label>
                                    <Input
                                        id="maxChars"
                                        type="number"
                                        value={maxChars}
                                        onChange={(e) => setMaxChars(parseInt(e.target.value) || 0)}
                                        min={1000}
                                        step={500}
                                    />
                                    <p className="text-[10px] text-zinc-500">建议 3000-8000 之间</p>
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label htmlFor="targetChunks">目标分块数</Label>
                                    <Input
                                        id="targetChunks"
                                        type="number"
                                        value={targetChunks}
                                        onChange={(e) => setTargetChunks(parseInt(e.target.value) || 0)}
                                        min={1}
                                        max={20}
                                    />
                                    <p className="text-[10px] text-zinc-500">生成的 PPT 大致页数</p>
                                </div>
                                <div className="flex items-center justify-end">
                                    <div className="flex items-center gap-3">
                                        <div className="space-y-0.5 text-right">
                                            <Label htmlFor="review">人工审核</Label>
                                            <p className="text-xs text-zinc-500">在大纲生成后先由人工确认</p>
                                        </div>
                                        <Switch
                                            id="review"
                                            checked={enableHumanReview}
                                            onCheckedChange={setEnableHumanReview}
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Action buttons */}
                <div className="flex gap-2">
                    {file && (
                        <Button
                            variant="outline"
                            onClick={() => setFile(null)}
                            disabled={uploading}
                            className="flex-1"
                        >
                            重新选择
                        </Button>
                    )}
                    <Button
                        onClick={handleUpload}
                        disabled={!file || uploading}
                        className="flex-1"
                    >
                        {uploading ? '处理中...' : '开始生成'}
                    </Button>
                </div>
            </CardContent>
        </Card>
    );
}
