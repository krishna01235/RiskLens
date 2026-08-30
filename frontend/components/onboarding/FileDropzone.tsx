"use client";

import { useState, useRef, DragEvent, ChangeEvent } from "react";
import { Upload, FileType, AlertCircle } from "lucide-react";

interface FileDropzoneProps {
  onFileSelect: (file: File) => void;
  isUploading: boolean;
  error?: string | null;
}

export default function FileDropzone({ onFileSelect, isUploading, error }: FileDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const validateAndSelectFile = (file: File) => {
    // Some OS report csv as application/vnd.ms-excel or text/plain
    if (file.name.endsWith(".csv") || file.type.includes("csv")) {
      onFileSelect(file);
    } else {
      // The parent component can handle showing an error, or we can just ignore
      // For now we just pass it, the backend will validate it too
      onFileSelect(file);
    }
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSelectFile(e.dataTransfer.files[0]);
      e.dataTransfer.clearData();
    }
  };

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSelectFile(e.target.files[0]);
    }
  };

  return (
    <div className="w-full">
      <div
        className={`relative flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-12 text-center transition-colors ${
          isDragging
            ? "border-violet-500 bg-violet-500/10"
            : error
              ? "border-red-500/50 bg-red-500/5"
              : "border-slate-700 bg-slate-900/50 hover:border-slate-500 hover:bg-slate-800/50"
        } ${isUploading ? "pointer-events-none opacity-50" : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv, text/csv"
          className="hidden"
          onChange={handleChange}
          disabled={isUploading}
        />
        
        <div className="mb-4 rounded-full bg-slate-800 p-4">
          <Upload className={`h-8 w-8 ${isDragging ? "text-violet-400" : "text-slate-400"}`} />
        </div>
        
        <h4 className="mb-2 text-lg font-medium text-slate-200">
          Click to upload or drag and drop
        </h4>
        <p className="text-sm text-slate-400">
          CSV files only. Make sure your file includes Symbol, Quantity, and Price columns.
        </p>
      </div>

      {error && (
        <div className="mt-4 flex items-center gap-2 text-sm text-red-400">
          <AlertCircle className="h-4 w-4" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
