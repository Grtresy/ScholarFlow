/**
 * ScholarFlow Main Application
 *
 * Academic Paper to Presentation Generator
 * Built with React, TypeScript, and LangGraph JS SDK
 */

import React, { useState, useEffect } from "react";
import { UploadForm, TaskStatus, HumanReview, Results } from "./components";
import { useWorkflow } from "./hooks/useWorkflow";
import type { WorkflowConfig } from "./lib/langgraph";

function App() {
  const [currentStep, setCurrentStep] = useState<"upload" | "processing" | "review" | "results">("upload");
  const [workflowConfig, setWorkflowConfig] = useState<WorkflowConfig | null>(null);

  const {
    state,
    isRunning,
    isPaused,
    error,
    startWorkflow,
    submitFeedback,
    cancelWorkflow,
    reset,
  } = useWorkflow();

  const handleUploadSuccess = async (uploadedPdfPath: string, uploadedTaskId: string) => {
    setCurrentStep("processing");

    // Start the workflow
    if (workflowConfig) {
      await startWorkflow(uploadedPdfPath, workflowConfig, uploadedTaskId);
    }
  };

  const handleWorkflowUpdate = () => {
    if (!state) return;

    if (state.status === "completed") {
      setCurrentStep("results");
    } else if (state.needs_human_review) {
      setCurrentStep("review");
    }
  };

  // Watch for state changes
  useEffect(() => {
    handleWorkflowUpdate();
  }, [state]);

  const handleReset = () => {
    reset();
    setCurrentStep("upload");
    setWorkflowConfig(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                ScholarFlow
              </h1>
              <p className="mt-1 text-sm text-gray-600">
                Academic Paper to Presentation Generator
              </p>
            </div>
            {(currentStep !== "upload" || isRunning || isPaused || state) && (
              <button
                onClick={handleReset}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
              >
                New Presentation
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Forms */}
          <div className="lg:col-span-2 space-y-6">
            {currentStep === "upload" && (
              <UploadForm
                onUploadSuccess={handleUploadSuccess}
                isUploading={isRunning}
                onConfigChange={setWorkflowConfig}
              />
            )}

            {currentStep === "review" && state && (
              <HumanReview
                state={state}
                onSubmitFeedback={submitFeedback}
                isSubmitting={isRunning}
              />
            )}

            {currentStep === "results" && state && <Results state={state} />}
          </div>

          {/* Right Column - Status */}
          <div className="lg:col-span-1">
            <TaskStatus
              state={state}
              isRunning={isRunning}
              isPaused={isPaused}
              error={error}
              onCancel={cancelWorkflow}
            />

            {/* Workflow Info */}
            {state && (
              <div className="bg-white rounded-lg shadow-md p-6 mt-6">
                <h3 className="text-lg font-semibold mb-3">Workflow Information</h3>
                <dl className="space-y-2 text-sm">
                  <div>
                    <dt className="font-medium text-gray-500">PDF Path</dt>
                    <dd className="text-gray-900 font-mono break-all">
                      {state.pdf_path}
                    </dd>
                  </div>
                  <div>
                    <dt className="font-medium text-gray-500">Presentation Style</dt>
                    <dd className="text-gray-900 capitalize">
                      {state.presentation_style.replace("_", " ")}
                    </dd>
                  </div>
                </dl>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-center text-sm text-gray-600">
            ScholarFlow v2.0.0 - Powered by LangGraph & LangChain
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
