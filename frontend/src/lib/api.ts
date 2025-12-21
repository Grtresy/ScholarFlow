/**
 * API client for ScholarFlow backend
 */

const getApiBaseUrl = () => {
    if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
    if (typeof window !== 'undefined') {
        const { protocol, hostname } = window.location;
        return `${protocol}//${hostname}:8000`;
    }
    return 'http://localhost:8000';
};

const API_BASE_URL = getApiBaseUrl();

// ===== Type Definitions =====

export enum TaskStatus {
    PENDING = 'pending',
    PARSING = 'parsing',
    SPLITTING = 'splitting',
    STAGE1_PROCESSING = 'stage1_processing',
    MERGING = 'merging',
    HUMAN_REVIEW = 'human_review',
    STAGE2_PROCESSING = 'stage2_processing',
    RENDERING = 'rendering',
    COMPLETED = 'completed',
    FAILED = 'failed',
    PAUSED = 'paused',
}

export interface ReviewPoint {
    type: string;
    node: string;
    content: string;
    prompt?: string;
    timestamp: string;
}

export interface TaskStatusResponse {
    task_id: string;
    status: string;
    progress_percentage: number;
    current_step: string;
    created_at: string;
    updated_at: string;
    error_message?: string;
    needs_human_review: boolean;
    review_points: ReviewPoint[];
}

export interface TaskResultResponse {
    task_id: string;
    status: string;
    pdf_path: string;
    output_path?: string;
    markdown_path?: string;
    chunks_count: number;
    stage1_completed: number;
    presentation_style: string;
    created_at: string;
    updated_at: string;
}

export interface UploadResponse {
    task_id: string;
    pdf_path: string;
    message: string;
    timestamp: string;
}

export interface CreateTaskRequest {
    pdf_path: string;
    presentation_style?: string;
    max_chars?: number;
    target_chunks?: number;
    output_format?: string;
    enable_human_review?: boolean;
    custom_stage1_prompt?: string;
    custom_stage2_prompt?: string;
}

export interface HumanFeedbackRequest {
    approved: boolean;
    action?: 'regenerate' | 'abort';
    comments?: string;
    modifications?: Record<string, any>;
}

// ===== API Functions =====

/**
 * Upload a PDF file
 */
export async function uploadPDF(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/api/upload`, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(error.detail || 'Failed to upload PDF');
    }

    return response.json();
}

/**
 * Create a new processing task
 */
export async function createTask(request: CreateTaskRequest): Promise<TaskStatusResponse> {
    const response = await fetch(`${API_BASE_URL}/api/tasks`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Task creation failed' }));
        throw new Error(error.detail || 'Failed to create task');
    }

    return response.json();
}

/**
 * Get task status
 */
export async function getTaskStatus(taskId: string): Promise<TaskStatusResponse> {
    const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}/status`);

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to get status' }));
        throw new Error(error.detail || 'Failed to get task status');
    }

    return response.json();
}

/**
 * Get task result
 */
export async function getTaskResult(taskId: string): Promise<TaskResultResponse> {
    const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}/result`);

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to get result' }));
        throw new Error(error.detail || 'Failed to get task result');
    }

    return response.json();
}

/**
 * Submit human feedback
 */
export async function submitHumanFeedback(
    taskId: string,
    feedback: HumanFeedbackRequest
): Promise<{ status: string; message: string; task_id: string }> {
    const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}/human-feedback`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(feedback),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to submit feedback' }));
        throw new Error(error.detail || 'Failed to submit feedback');
    }

    return response.json();
}

/**
 * Download generated presentation
 */
export async function downloadPresentation(taskId: string): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/api/download/${taskId}`);

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Download failed' }));
        throw new Error(error.detail || 'Failed to download presentation');
    }

    return response.blob();
}

/**
 * Helper function to trigger file download in browser
 */
export function triggerDownload(blob: Blob, filename: string) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

/**
 * Get available prompt templates
 */
export async function getPromptTemplates(): Promise<{ stage1: Record<string, string>; stage2: Record<string, string> }> {
    const response = await fetch(`${API_BASE_URL}/api/prompts/templates`);

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to get templates' }));
        throw new Error(error.detail || 'Failed to get prompt templates');
    }

    return response.json();
}

/**
 * Get markdown content for a task
 */
export async function getMarkdownContent(
    taskId: string,
    stage?: string
): Promise<{ task_id: string; content: string; stage: string; updated_at?: string }> {
    const url = new URL(`${API_BASE_URL}/api/tasks/${taskId}/markdown`);
    if (stage) {
        url.searchParams.append('stage', stage);
    }

    const response = await fetch(url.toString());

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to get markdown' }));
        throw new Error(error.detail || 'Failed to get markdown content');
    }

    return response.json();
}

/**
 * Save markdown content for a task
 */
export async function saveMarkdownContent(
    taskId: string,
    content: string,
    stage: string = 'marp_markdown'
): Promise<{ status: string; message: string; task_id: string }> {
    const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}/markdown`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content, stage }),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to save markdown' }));
        throw new Error(error.detail || 'Failed to save markdown content');
    }

    return response.json();
}

/**
 * Save original version of presentation when entering editor
 */
export async function saveOriginalVersion(taskId: string): Promise<{ status: string; message: string; output_path: string; markdown_path: string }> {
    const response = await fetch(`${API_BASE_URL}/api/save-original/${taskId}`, {
        method: 'POST',
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to save original version' }));
        throw new Error(error.detail || 'Failed to save original version');
    }

    return response.json();
}

/**
 * Render markdown preview
 */
export async function renderPreview(
    markdown: string,
    taskId?: string,
    baseUrl?: string
): Promise<{ html: string }> {
    const response = await fetch(`${API_BASE_URL}/api/render/preview`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            markdown,
            task_id: taskId,
            base_url: baseUrl,
        }),
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to render preview' }));
        throw new Error(error.detail || 'Failed to render preview');
    }

    return response.json();
}
