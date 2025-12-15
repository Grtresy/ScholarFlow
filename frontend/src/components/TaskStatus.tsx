/**
 * Task Status Component
 *
 * Displays real-time progress of the workflow execution.
 */

import type { WorkflowState } from "../lib/langgraph";

interface TaskStatusProps {
  state: WorkflowState | null;
  isRunning: boolean;
  isPaused: boolean;
  error: string | null;
  onCancel: () => void;
}

const WORKFLOW_STEPS = [
  { key: "initialization", label: "Initializing" },
  { key: "parse_pdf", label: "Parsing PDF" },
  { key: "split_markdown", label: "Splitting Content" },
  { key: "stage1_process", label: "Generating Outlines" },
  { key: "merge_outlines", label: "Merging Outlines" },
  { key: "human_review", label: "Waiting for Review" },
  { key: "stage2_process", label: "Converting to Presentation" },
  { key: "render", label: "Rendering" },
  { key: "completed", label: "Completed" },
];

export function TaskStatus({
  state,
  isRunning,
  isPaused,
  error,
  onCancel,
}: TaskStatusProps) {
  if (!state && !isRunning && !isPaused && !error) {
    return null;
  }

  const getStepIndex = (currentStep: string) => {
    const index = WORKFLOW_STEPS.findIndex((step) => step.key === currentStep);
    return index >= 0 ? index : 0;
  };

  const currentStepIndex = state ? getStepIndex(state.current_step) : 0;
  const progress = state?.progress_percentage || 0;

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mt-6">
      <h2 className="text-2xl font-bold mb-4">Workflow Status</h2>

      {/* Error Display */}
      {error && (
        <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg">
          <div className="flex items-start">
            <svg
              className="h-5 w-5 mr-2 mt-0.5"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
            <div>
              <p className="font-medium">Error Occurred</p>
              <p className="text-sm">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Status Display */}
      {state && (
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Status</span>
            <span
              className={`px-3 py-1 rounded-full text-sm font-medium ${
                state.status === "completed"
                  ? "bg-green-100 text-green-800"
                  : state.status === "error"
                  ? "bg-red-100 text-red-800"
                  : isPaused
                  ? "bg-yellow-100 text-yellow-800"
                  : "bg-blue-100 text-blue-800"
              }`}
            >
              {state.status === "completed"
                ? "✓ Completed"
                : state.status === "error"
                ? "✗ Error"
                : isPaused
                ? "⏸ Paused"
                : "⟳ Running"}
            </span>
          </div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Current Step</span>
            <span className="text-sm text-gray-600">
              {state.current_step
                .split("_")
                .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
                .join(" ")}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">Task ID</span>
            <span className="text-sm text-gray-600 font-mono">{state.task_id}</span>
          </div>
        </div>
      )}

      {/* Progress Bar */}
      {(isRunning || isPaused || state) && (
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">
              Progress
            </span>
            <span className="text-sm text-gray-600">{progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div
              className={`h-3 rounded-full transition-all duration-300 ${
                state?.status === "error"
                  ? "bg-red-500"
                  : isPaused
                  ? "bg-yellow-500"
                  : "bg-blue-600"
              }`}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Workflow Steps */}
      {(isRunning || isPaused || state) && (
        <div className="mb-6">
          <h3 className="text-sm font-medium text-gray-700 mb-3">
            Workflow Steps
          </h3>
          <div className="space-y-2">
            {WORKFLOW_STEPS.map((step, index) => {
              const isCompleted = index < currentStepIndex;
              const isCurrent = index === currentStepIndex && (isRunning || isPaused);

              return (
                <div
                  key={step.key}
                  className={`flex items-center p-2 rounded ${
                    isCurrent ? "bg-blue-50" : ""
                  }`}
                >
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center mr-3 ${
                      isCompleted
                        ? "bg-green-500 text-white"
                        : isCurrent
                        ? "bg-blue-600 text-white"
                        : "bg-gray-200 text-gray-600"
                    }`}
                  >
                    {isCompleted ? (
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                    ) : isCurrent ? (
                      <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
                    ) : (
                      <span className="text-xs">{index + 1}</span>
                    )}
                  </div>
                  <span
                    className={`text-sm ${
                      isCompleted
                        ? "text-green-700 font-medium"
                        : isCurrent
                        ? "text-blue-700 font-medium"
                        : "text-gray-500"
                    }`}
                  >
                    {step.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Cancel Button */}
      {(isRunning || isPaused) && (
        <button
          onClick={onCancel}
          className="w-full py-2 px-4 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
        >
          Cancel Workflow
        </button>
      )}
    </div>
  );
}
