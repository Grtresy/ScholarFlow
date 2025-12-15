/**
 * Human Review Component
 *
 * Allows users to review and approve/reject the generated outline
 * before proceeding to the final rendering stage.
 */

import { useState } from "react";
import type { WorkflowState } from "../lib/langgraph";

interface HumanReviewProps {
  state: WorkflowState;
  onSubmitFeedback: (approved: boolean, comments?: string) => Promise<void>;
  isSubmitting: boolean;
}

export function HumanReview({
  state,
  onSubmitFeedback,
  isSubmitting,
}: HumanReviewProps) {
  const [approved, setApproved] = useState<boolean | null>(null);
  const [comments, setComments] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (!state.needs_human_review) {
    return null;
  }

  const handleSubmit = async () => {
    if (approved === null) {
      setError("Please select approve or reject");
      return;
    }

    try {
      setError(null);
      await onSubmitFeedback(approved, comments || undefined);
      // Reset form on success
      setApproved(null);
      setComments("");
    } catch (err) {
      console.error("Error submitting feedback:", err);
      setError(
        err instanceof Error
          ? err.message
          : "Failed to submit feedback. Please try again."
      );
    }
  };

  const mergedOutline = state.merged_outline || state.outlines?.[0];

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mt-6">
      <h2 className="text-2xl font-bold mb-4">Review Generated Outline</h2>

      <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <div className="flex items-start">
          <svg
            className="h-5 w-5 text-yellow-600 mr-2 mt-0.5"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
          <div>
            <p className="text-sm font-medium text-yellow-800">
              Your approval is required to continue
            </p>
            <p className="text-sm text-yellow-700 mt-1">
              Please review the generated outline below and approve or reject it.
            </p>
          </div>
        </div>
      </div>

      {/* Outline Display */}
      {mergedOutline && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold mb-3">Generated Outline</h3>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 max-h-96 overflow-y-auto">
            <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans">
              {JSON.stringify(mergedOutline, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {error && (
        <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}

      {/* Approval/Rejection */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-3">
          Do you approve this outline?
        </label>
        <div className="space-y-2">
          <label className="flex items-center p-3 border border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50">
            <input
              type="radio"
              name="approval"
              value="approve"
              checked={approved === true}
              onChange={() => setApproved(true)}
              className="h-4 w-4 text-green-600 focus:ring-green-500 border-gray-300"
              disabled={isSubmitting}
            />
            <span className="ml-3 text-sm text-gray-700">
              ✓ Yes, approve and continue to rendering
            </span>
          </label>
          <label className="flex items-center p-3 border border-gray-300 rounded-lg cursor-pointer hover:bg-gray-50">
            <input
              type="radio"
              name="approval"
              value="reject"
              checked={approved === false}
              onChange={() => setApproved(false)}
              className="h-4 w-4 text-red-600 focus:ring-red-500 border-gray-300"
              disabled={isSubmitting}
            />
            <span className="ml-3 text-sm text-gray-700">
              ✗ No, reject and provide feedback
            </span>
          </label>
        </div>
      </div>

      {/* Comments */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Comments (optional)
        </label>
        <textarea
          value={comments}
          onChange={(e) => setComments(e.target.value)}
          placeholder={
            approved === false
              ? "Please explain what changes you'd like to see..."
              : "Any additional comments or feedback..."
          }
          rows={4}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          disabled={isSubmitting}
        />
      </div>

      {/* Submit Button */}
      <button
        onClick={handleSubmit}
        disabled={approved === null || isSubmitting}
        className={`w-full py-3 px-4 rounded-md font-medium transition-colors ${
          approved === null || isSubmitting
            ? "bg-gray-300 text-gray-500 cursor-not-allowed"
            : approved
            ? "bg-green-600 text-white hover:bg-green-700"
            : "bg-red-600 text-white hover:bg-red-700"
        }`}
      >
        {isSubmitting ? "Submitting..." : "Submit Feedback"}
      </button>
    </div>
  );
}
