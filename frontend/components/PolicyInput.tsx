"use client";
import { useState } from "react";
import { PolicyPreset } from "@/lib/types";

interface Props {
  presets: PolicyPreset[];
  onSimulate: (policy: string) => void;
  isLoading: boolean;
}

const categoryColors: Record<string, string> = {
  road_closure: "bg-red-100 text-red-800 border-red-200",
  new_route: "bg-blue-100 text-blue-800 border-blue-200",
  signal_timing: "bg-yellow-100 text-yellow-800 border-yellow-200",
  transit_add: "bg-green-100 text-green-800 border-green-200",
};

export default function PolicyInput({ presets, onSimulate, isLoading }: Props) {
  const [policy, setPolicy] = useState("");
  const [selected, setSelected] = useState<string | null>(null);

  const handlePreset = (preset: PolicyPreset) => {
    setPolicy(preset.description);
    setSelected(preset.id);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (policy.trim() && !isLoading) {
      onSimulate(policy.trim());
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">
          Policy Presets
        </h2>
        <div className="flex flex-col gap-2">
          {presets.map((preset) => (
            <button
              key={preset.id}
              onClick={() => handlePreset(preset)}
              className={`text-left rounded-lg border p-3 transition-all hover:shadow-sm ${
                selected === preset.id
                  ? "border-indigo-400 bg-indigo-50 shadow-sm"
                  : "border-gray-200 bg-white hover:border-gray-300"
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="text-base">{preset.icon}</span>
                <span className="text-sm font-medium text-gray-800">{preset.title}</span>
              </div>
              <span
                className={`inline-block text-xs px-2 py-0.5 rounded-full border ${
                  categoryColors[preset.category] || "bg-gray-100 text-gray-600"
                }`}
              >
                {preset.category.replace("_", " ")}
              </span>
            </button>
          ))}
        </div>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <div>
          <label className="block text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">
            Custom Policy
          </label>
          <textarea
            value={policy}
            onChange={(e) => {
              setPolicy(e.target.value);
              setSelected(null);
            }}
            placeholder="Describe a traffic or mobility policy to test... e.g. 'Add a dedicated cycle lane along Lakeshore Road from Ernakulam to Marine Drive'"
            className="w-full h-28 text-sm rounded-lg border border-gray-200 p-3 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent placeholder-gray-400"
            disabled={isLoading}
          />
        </div>
        <button
          type="submit"
          disabled={!policy.trim() || isLoading}
          className={`w-full py-3 rounded-lg text-sm font-semibold transition-all ${
            !policy.trim() || isLoading
              ? "bg-gray-200 text-gray-400 cursor-not-allowed"
              : "bg-indigo-600 text-white hover:bg-indigo-700 active:scale-95 shadow-sm"
          }`}
        >
          {isLoading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full" />
              Simulating...
            </span>
          ) : (
            "Run Simulation →"
          )}
        </button>
      </form>
    </div>
  );
}
