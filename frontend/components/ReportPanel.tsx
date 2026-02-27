"use client";
import ReactMarkdown from "react-markdown";

interface Props {
  recommendations: string | null;
  isLoading: boolean;
}

export default function ReportPanel({ recommendations, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="flex flex-col gap-3 animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-2/3" />
        <div className="h-3 bg-gray-200 rounded w-full" />
        <div className="h-3 bg-gray-200 rounded w-5/6" />
        <div className="h-3 bg-gray-200 rounded w-4/5" />
        <div className="h-4 bg-gray-200 rounded w-1/2 mt-2" />
        <div className="h-3 bg-gray-200 rounded w-full" />
        <div className="h-3 bg-gray-200 rounded w-3/4" />
      </div>
    );
  }

  if (!recommendations) {
    return (
      <div className="text-sm text-gray-400 text-center py-8">
        Policy recommendation report will appear here after simulation
      </div>
    );
  }

  return (
    <div className="prose prose-sm max-w-none text-gray-700">
      <ReactMarkdown
        components={{
          h2: ({ children }) => (
            <h2 className="text-sm font-bold text-gray-900 uppercase tracking-wider mt-4 mb-2 border-b border-gray-100 pb-1">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-sm font-semibold text-gray-800 mt-3 mb-1">{children}</h3>
          ),
          p: ({ children }) => (
            <p className="text-sm text-gray-600 mb-2 leading-relaxed">{children}</p>
          ),
          ul: ({ children }) => (
            <ul className="list-disc list-inside text-sm text-gray-600 mb-2 space-y-1">
              {children}
            </ul>
          ),
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          strong: ({ children }) => (
            <strong className="font-semibold text-gray-900">{children}</strong>
          ),
        }}
      >
        {recommendations}
      </ReactMarkdown>
    </div>
  );
}
