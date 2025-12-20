'use client';

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';

interface MarkdownPreviewProps {
    content: string;
    className?: string;
    showLineNumbers?: boolean;
    maxHeight?: string;
}

export function MarkdownPreview({
    content,
    className = '',
    showLineNumbers = false,
    maxHeight = '600px',
}: MarkdownPreviewProps) {
    return (
        <div className={`markdown-preview ${className}`}>
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
                components={{
                    // Headings
                    h1: ({ node, ...props }) => (
                        <h1
                            {...props}
                            className="text-3xl font-bold mt-6 mb-4 text-zinc-900 dark:text-zinc-100"
                        />
                    ),
                    h2: ({ node, ...props }) => (
                        <h2
                            {...props}
                            className="text-2xl font-bold mt-5 mb-3 text-zinc-900 dark:text-zinc-100"
                        />
                    ),
                    h3: ({ node, ...props }) => (
                        <h3
                            {...props}
                            className="text-xl font-semibold mt-4 mb-2 text-zinc-900 dark:text-zinc-100"
                        />
                    ),
                    h4: ({ node, ...props }) => (
                        <h4
                            {...props}
                            className="text-lg font-semibold mt-3 mb-2 text-zinc-800 dark:text-zinc-200"
                        />
                    ),

                    // Paragraphs
                    p: ({ node, ...props }) => (
                        <p
                            {...props}
                            className="mb-4 text-zinc-700 dark:text-zinc-300 leading-relaxed"
                        />
                    ),

                    // Lists
                    ul: ({ node, ...props }) => (
                        <ul
                            {...props}
                            className="mb-4 ml-6 list-disc space-y-2 text-zinc-700 dark:text-zinc-300"
                        />
                    ),
                    ol: ({ node, ...props }) => (
                        <ol
                            {...props}
                            className="mb-4 ml-6 list-decimal space-y-2 text-zinc-700 dark:text-zinc-300"
                        />
                    ),
                    li: ({ node, ...props }) => (
                        <li {...props} className="text-zinc-700 dark:text-zinc-300" />
                    ),

                    // Links
                    a: ({ node, ...props }) => (
                        <a
                            {...props}
                            className="text-blue-600 dark:text-blue-400 hover:underline"
                            target="_blank"
                            rel="noopener noreferrer"
                        />
                    ),

                    // Images
                    img: ({ node, ...props }) => (
                        <img
                            {...props}
                            className="rounded-lg my-4 max-w-full h-auto border border-zinc-200 dark:border-zinc-700"
                            loading="lazy"
                        />
                    ),

                    // Blockquotes
                    blockquote: ({ node, ...props }) => (
                        <blockquote
                            {...props}
                            className="border-l-4 border-blue-500 pl-4 py-2 my-4 bg-blue-50 dark:bg-blue-950/20 text-zinc-700 dark:text-zinc-300 italic"
                        />
                    ),

                    // Code blocks
                    code: ({ node, inline, className, ...props }) => {
                        const match = /language-(\w+)/.exec(className || '');
                        return !inline ? (
                            <pre className="bg-zinc-100 dark:bg-zinc-900 rounded-lg p-4 overflow-auto my-4">
                                <code className={className} {...props} />
                            </pre>
                        ) : (
                            <code
                                className="bg-zinc-100 dark:bg-zinc-800 px-1.5 py-0.5 rounded text-sm font-mono text-zinc-800 dark:text-zinc-200"
                                {...props}
                            />
                        );
                    },

                    // Tables
                    table: ({ node, ...props }) => (
                        <div className="overflow-auto my-4">
                            <table
                                {...props}
                                className="min-w-full border-collapse border border-zinc-300 dark:border-zinc-700"
                            />
                        </div>
                    ),
                    thead: ({ node, ...props }) => (
                        <thead {...props} className="bg-zinc-100 dark:bg-zinc-800" />
                    ),
                    th: ({ node, ...props }) => (
                        <th
                            {...props}
                            className="border border-zinc-300 dark:border-zinc-700 px-4 py-2 text-left font-semibold text-zinc-900 dark:text-zinc-100"
                        />
                    ),
                    td: ({ node, ...props }) => (
                        <td
                            {...props}
                            className="border border-zinc-300 dark:border-zinc-700 px-4 py-2 text-zinc-700 dark:text-zinc-300"
                        />
                    ),

                    // Horizontal rule
                    hr: ({ node, ...props }) => (
                        <hr
                            {...props}
                            className="my-6 border-zinc-300 dark:border-zinc-700"
                        />
                    ),

                    // Strong and emphasis
                    strong: ({ node, ...props }) => (
                        <strong {...props} className="font-bold text-zinc-900 dark:text-zinc-100" />
                    ),
                    em: ({ node, ...props }) => (
                        <em {...props} className="italic text-zinc-800 dark:text-zinc-200" />
                    ),
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
}
