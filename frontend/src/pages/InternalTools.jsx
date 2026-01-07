import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { apiClient } from "../lib/supabase-auth";

const fetchUsageStats = async () => {
  const { data } = await apiClient.get("/api/usage/me?days=30");
  return data;
};

const useTool = async (toolName, action, metadata) => {
  const { data } = await apiClient.post(`/api/tools/${toolName}`, {
    action,
    metadata,
  });
  return data;
};

export default function InternalTools() {
  const { data: usageStats, refetch } = useQuery({
    queryKey: ["usage-stats"],
    queryFn: fetchUsageStats,
  });

  const [selectedTool, setSelectedTool] = useState("aircraft-matcher");
  const [toolInput, setToolInput] = useState("");
  const [toolResult, setToolResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleToolSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setToolResult(null);

    try {
      const result = await useTool(selectedTool, "execute", {
        input: toolInput,
        timestamp: Date.now(),
      });
      setToolResult(result);
      refetch(); // Refresh usage stats
    } catch (error) {
      setToolResult({ error: error.message });
    } finally {
      setLoading(false);
    }
  };

  const tools = [
    {
      id: "aircraft-matcher",
      name: "Aircraft Matcher",
      description: "Match aircraft based on your requirements and preferences",
    },
    {
      id: "scoring",
      name: "Aircraft Scoring",
      description: "Score and compare aircraft based on your priorities",
    },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Internal Tools</h1>
        <p className="mt-2 text-sm text-gray-600">
          Use our built-in tools to help find the perfect aircraft for your needs.
        </p>
      </div>

      {/* Usage Statistics */}
      {usageStats && (
        <div className="mb-8 bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">Your Usage (Last 30 Days)</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <div className="text-2xl font-bold text-indigo-600">
                {usageStats.total_usage || 0}
              </div>
              <div className="text-sm text-gray-500">Total Uses</div>
            </div>
            {usageStats.by_tool?.map((tool) => (
              <div key={tool.tool_name}>
                <div className="text-xl font-semibold text-gray-900">{tool.count}</div>
                <div className="text-sm text-gray-500 capitalize">
                  {tool.tool_name.replace("-", " ")}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tool Selection */}
      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Select Tool</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {tools.map((tool) => (
            <button
              key={tool.id}
              onClick={() => setSelectedTool(tool.id)}
              className={`p-4 border-2 rounded-lg text-left transition-colors ${
                selectedTool === tool.id
                  ? "border-indigo-600 bg-indigo-50"
                  : "border-gray-200 hover:border-gray-300"
              }`}
            >
              <h3 className="font-medium text-gray-900">{tool.name}</h3>
              <p className="mt-1 text-sm text-gray-500">{tool.description}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Tool Interface */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">
          {tools.find((t) => t.id === selectedTool)?.name}
        </h2>
        <form onSubmit={handleToolSubmit} className="space-y-4">
          <div>
            <label htmlFor="tool-input" className="block text-sm font-medium text-gray-700">
              Enter your requirements
            </label>
            <textarea
              id="tool-input"
              rows={4}
              value={toolInput}
              onChange={(e) => setToolInput(e.target.value)}
              className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              placeholder="Describe what you're looking for..."
            />
          </div>
          <button
            type="submit"
            disabled={loading || !toolInput.trim()}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Processing..." : "Run Tool"}
          </button>
        </form>

        {/* Tool Results */}
        {toolResult && (
          <div className="mt-6 p-4 bg-gray-50 rounded-lg">
            <h3 className="text-sm font-medium text-gray-900 mb-2">Results</h3>
            {toolResult.error ? (
              <div className="text-sm text-red-600">{toolResult.error}</div>
            ) : (
              <pre className="text-sm text-gray-700 whitespace-pre-wrap">
                {JSON.stringify(toolResult.result, null, 2)}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

