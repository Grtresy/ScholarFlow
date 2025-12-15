/**
 * LangGraph SDK client configuration for ScholarFlow.
 *
 * This module provides the LangGraph client instance and configuration
 * for connecting to the LangGraph server from the React frontend.
 */

import { Client } from "@langchain/langgraph-sdk";

// Get API URLs from environment variables
const API_URL = import.meta.env.VITE_LANGGRAPH_URL || "http://localhost:8123";

// Create LangGraph client instance
export const client = new Client({
  apiUrl: API_URL,
});

// Name of the workflow graph in the LangGraph server
export const GRAPH_NAME = "scholarflow";

// Types for workflow state
export interface WorkflowConfig {
  presentation_style: "academic" | "popular_science" | "business_pitch";
  max_chars: number;
  target_chunks: number;
}

export interface WorkflowState {
  task_id: string;
  pdf_path: string;
  presentation_style: string;
  status: string;
  current_step: string;
  progress_percentage: number;
  needs_human_review: boolean;
  human_feedback?: {
    approved: boolean;
    comments?: string;
  };
  markdown_content?: string;
  chunks?: any[];
  outlines?: any[];
  merged_outline?: any;
  final_marp_markdown?: string;
  output_path?: string;
  error_message?: string;
  logs?: string[];
}

// Helper function to create initial state
export function createInitialState(
  taskId: string,
  pdfPath: string,
  config: WorkflowConfig
): WorkflowState {
  return {
    task_id: taskId,
    pdf_path: pdfPath,
    presentation_style: config.presentation_style,
    status: "pending",
    current_step: "initialization",
    progress_percentage: 0,
    needs_human_review: false,
  };
}
