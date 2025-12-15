/**
 * PDF Upload Form Component
 *
 * Allows users to upload PDF files and configure workflow settings.
 */

import React, { useState, useRef } from "react";
import axios from "axios";
import type { WorkflowConfig } from "../lib/langgraph";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface UploadFormProps {
  onUploadSuccess: (pdfPath: string, taskId: string) => void;
  isUploading: boolean;
  onConfigChange: (config: WorkflowConfig) => void;
}

export function UploadForm({ onUploadSuccess, isUploading, onConfigChange }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [presentationStyle, setPresentationStyle] = useState<"academic" | "popular_science" | "business_pitch">("academic");
  const [maxChars, setMaxChars] = useState(6000);
  const [targetChunks, setTargetChunks] = useState(6);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Update config when settings change
  React.useEffect(() => {
    onConfigChange({
      presentation_style: presentationStyle,
      max_chars: maxChars,
      target_chunks: targetChunks,
    });
  }, [presentationStyle, maxChars, targetChunks, onConfigChange]);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type === "application/pdf") {
        setFile(droppedFile);
        setUploadError(null);
      } else {
        setUploadError("Only PDF files are allowed");
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (selectedFile.type === "application/pdf") {
        setFile(selectedFile);
        setUploadError(null);
      } else {
        setUploadError("Only PDF files are allowed");
      }
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setUploadError("Please select a PDF file");
      return;
    }

    try {
      setUploadError(null);
      const formData = new FormData();
      formData.append("file", file);

      const response = await axios.post(`${API_URL}/api/upload`, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      const { task_id, pdf_path } = response.data;

      // Call parent callback with the uploaded file info
      onUploadSuccess(pdf_path, task_id);

      // Reset form
      setFile(null);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    } catch (err) {
      console.error("Upload error:", err);
      setUploadError(
        err instanceof Error
          ? err.message
          : "Failed to upload file. Please try again."
      );
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-2xl font-bold mb-4">Upload PDF Paper</h2>

      {/* File Upload Area */}
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          dragActive
            ? "border-blue-500 bg-blue-50"
            : "border-gray-300 hover:border-gray-400"
        } ${file ? "bg-green-50 border-green-500" : ""}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          onChange={handleFileSelect}
          className="hidden"
        />
        {file ? (
          <div className="text-green-600">
            <svg
              className="mx-auto h-12 w-12"
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
            <p className="mt-2 font-medium">{file.name}</p>
            <p className="text-sm text-gray-500">
              {(file.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </div>
        ) : (
          <div>
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            <p className="mt-2 text-gray-600">
              Drag and drop your PDF file here, or click to select
            </p>
          </div>
        )}
      </div>

      {uploadError && (
        <div className="mt-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
          {uploadError}
        </div>
      )}

      {/* Configuration Options */}
      <div className="mt-6 space-y-4">
        <h3 className="text-lg font-semibold">Presentation Settings</h3>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Presentation Style
          </label>
          <select
            value={presentationStyle}
            onChange={(e) =>
              setPresentationStyle(e.target.value as any)
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isUploading}
          >
            <option value="academic">Academic</option>
            <option value="popular_science">Popular Science</option>
            <option value="business_pitch">Business Pitch</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Max Characters per Chunk
          </label>
          <input
            type="number"
            value={maxChars}
            onChange={(e) => setMaxChars(Number(e.target.value))}
            min={1000}
            max={10000}
            step={500}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isUploading}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Target Number of Chunks
          </label>
          <input
            type="number"
            value={targetChunks}
            onChange={(e) => setTargetChunks(Number(e.target.value))}
            min={3}
            max={20}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isUploading}
          />
        </div>
      </div>

      {/* Upload Button */}
      <button
        onClick={handleUpload}
        disabled={!file || isUploading}
        className={`mt-6 w-full py-3 px-4 rounded-md font-medium transition-colors ${
          !file || isUploading
            ? "bg-gray-300 text-gray-500 cursor-not-allowed"
            : "bg-blue-600 text-white hover:bg-blue-700"
        }`}
      >
        {isUploading ? "Uploading..." : "Upload and Start"}
      </button>
    </div>
  );
}
