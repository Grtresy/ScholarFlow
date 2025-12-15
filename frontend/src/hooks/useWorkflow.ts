/**
 * React hook for orchestrating the ScholarFlow workflow.
 *
 * This hook provides:
 * - Workflow state management
 * - Thread creation and management
 * - Run streaming for real-time updates
 * - Human feedback submission
 */

import { useState, useCallback, useRef } from "react";
import { client, GRAPH_NAME, createInitialState } from "../lib/langgraph";
import type { WorkflowState, WorkflowConfig } from "../lib/langgraph";

interface UseWorkflowReturn {
  threadId: string | null;
  state: WorkflowState | null;
  isRunning: boolean;
  isPaused: boolean;
  error: string | null;
  startWorkflow: (pdfPath: string, config: WorkflowConfig, taskId: string) => Promise<void>;
  submitFeedback: (approved: boolean, comments?: string) => Promise<void>;
  cancelWorkflow: () => Promise<void>;
  reset: () => void;
}

export function useWorkflow(): UseWorkflowReturn {
  const [threadId, setThreadId] = useState<string | null>(null);
  const [state, setState] = useState<WorkflowState | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    setThreadId(null);
    setState(null);
    setIsRunning(false);
    setIsPaused(false);
    setError(null);
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  }, []);

  const startWorkflow = useCallback(async (
    pdfPath: string,
    config: WorkflowConfig,
    taskId: string
  ) => {
    try {
      setError(null);
      setIsRunning(true);
      setIsPaused(false);

      // Create a new thread
      const thread = await client.threads.create();
      setThreadId(thread.thread_id);

      // Create initial state
      const initialState = createInitialState(taskId, pdfPath, config);

      // Create abort controller for this run
      abortControllerRef.current = new AbortController();

      // Start the workflow
      const run = await client.runs.create(
        thread.thread_id,
        GRAPH_NAME,
        {
          input: initialState,
          signal: abortControllerRef.current.signal,
        }
      );

      // Stream updates
      for await (const chunk of client.runs.stream(thread.thread_id, run.run_id)) {
        if (chunk.data) {
          setState(chunk.data);

          // Check if workflow is paused (waiting for human review)
          if (chunk.data.needs_human_review) {
            setIsPaused(true);
            setIsRunning(false);
          }

          // Check if workflow is completed
          if (chunk.data.status === "completed" || chunk.data.status === "error") {
            setIsRunning(false);
            if (chunk.data.status === "error") {
              setError(chunk.data.error_message || "Workflow failed");
            }
          }
        }
      }
    } catch (err) {
      console.error("Error starting workflow:", err);
      setError(err instanceof Error ? err.message : "Failed to start workflow");
      setIsRunning(false);
    }
  }, []);

  const submitFeedback = useCallback(async (approved: boolean, comments?: string) => {
    if (!threadId || !state?.needs_human_review) {
      throw new Error("Workflow is not paused for review");
    }

    try {
      setError(null);

      // Resume the workflow with human feedback
      const run = await client.runs.create(
        threadId,
        GRAPH_NAME,
        {
          input: {
            ...state,
            human_feedback: {
              approved,
              comments,
            },
            needs_human_review: false,
          },
        }
      );

      // Continue streaming updates
      for await (const chunk of client.runs.stream(threadId, run.run_id)) {
        if (chunk.data) {
          setState(chunk.data);

          if (chunk.data.status === "completed" || chunk.data.status === "error") {
            setIsRunning(false);
            setIsPaused(false);
            if (chunk.data.status === "error") {
              setError(chunk.data.error_message || "Workflow failed");
            }
          }
        }
      }
    } catch (err) {
      console.error("Error submitting feedback:", err);
      setError(err instanceof Error ? err.message : "Failed to submit feedback");
    }
  }, [threadId, state]);

  const cancelWorkflow = useCallback(async () => {
    if (!threadId) {
      return;
    }

    try {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      setIsRunning(false);
      setIsPaused(false);
    } catch (err) {
      console.error("Error cancelling workflow:", err);
      setError(err instanceof Error ? err.message : "Failed to cancel workflow");
    }
  }, [threadId]);

  return {
    threadId,
    state,
    isRunning,
    isPaused,
    error,
    startWorkflow,
    submitFeedback,
    cancelWorkflow,
    reset,
  };
}
