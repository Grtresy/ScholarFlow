/**
 * Results Component
 *
 * Displays the final generated presentation and allows downloading.
 */

import type { WorkflowState } from "../lib/langgraph";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface ResultsProps {
  state: WorkflowState;
}

export function Results({ state }: ResultsProps) {
  if (state.status !== "completed" || !state.output_path) {
    return null;
  }

  const handleDownload = () => {
    const downloadUrl = `${API_URL}/api/download/${state.task_id}`;
    window.open(downloadUrl, "_blank");
  };

  const finalMarkdown = state.final_marp_markdown;

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mt-6">
      <h2 className="text-2xl font-bold mb-4">Presentation Generated Successfully</h2>

      <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
        <div className="flex items-start">
          <svg
            className="h-5 w-5 text-green-600 mr-2 mt-0.5"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
              clipRule="evenodd"
            />
          </svg>
          <div>
            <p className="text-sm font-medium text-green-800">
              Your presentation is ready!
            </p>
            <p className="text-sm text-green-700 mt-1">
              You can download it below or view the generated Marp Markdown.
            </p>
          </div>
        </div>
      </div>

      {/* Task Summary */}
      <div className="mb-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
        <h3 className="text-lg font-semibold mb-3">Task Summary</h3>
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <dt className="text-sm font-medium text-gray-500">Task ID</dt>
            <dd className="mt-1 text-sm text-gray-900 font-mono">
              {state.task_id}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Presentation Style</dt>
            <dd className="mt-1 text-sm text-gray-900 capitalize">
              {state.presentation_style.replace("_", " ")}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Output File</dt>
            <dd className="mt-1 text-sm text-gray-900 font-mono">
              {state.output_path.split("/").pop()}
            </dd>
          </div>
          <div>
            <dt className="text-sm font-medium text-gray-500">Total Slides</dt>
            <dd className="mt-1 text-sm text-gray-900">
              {state.merged_outline?.slides?.length || "N/A"}
            </dd>
          </div>
        </dl>
      </div>

      {/* Download Button */}
      <button
        onClick={handleDownload}
        className="w-full mb-6 py-3 px-4 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors font-medium flex items-center justify-center"
      >
        <svg
          className="w-5 h-5 mr-2"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
          />
        </svg>
        Download Presentation
      </button>

      {/* Marp Markdown Preview */}
      {finalMarkdown && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold mb-3">
            Generated Marp Markdown
          </h3>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 max-h-96 overflow-y-auto">
            <pre className="text-sm text-gray-700 whitespace-pre-wrap font-mono">
              {finalMarkdown}
            </pre>
          </div>
          <button
            onClick={() => {
              navigator.clipboard.writeText(finalMarkdown);
              alert("Copied to clipboard!");
            }}
            className="mt-2 px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors text-sm"
          >
            Copy to Clipboard
          </button>
        </div>
      )}

      {/* Outline Structure */}
      {state.merged_outline && (
        <div>
          <h3 className="text-lg font-semibold mb-3">Presentation Structure</h3>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans">
              {JSON.stringify(state.merged_outline, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
