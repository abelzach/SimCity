"use client";
import { useEffect, useState, useCallback, useRef } from "react";
import dynamic from "next/dynamic";

import PolicyInput from "@/components/PolicyInput";
import AgentTimeline from "@/components/AgentTimeline";
import ImpactMetrics from "@/components/ImpactMetrics";
import ReportPanel from "@/components/ReportPanel";

import {
  fetchPresets,
  fetchKochiGeoJSON,
  fetchBaselineMetrics,
  startSimulation,
} from "@/lib/api";
import type {
  PolicyPreset,
  AgentStatus,
  ImpactScores,
  BaselineMetrics,
  GeoJSONFeatureCollection,
  StreamEvent,
} from "@/lib/types";

// Leaflet must be loaded client-side only
const CityMap = dynamic(() => import("@/components/CityMap"), { ssr: false });

const AGENT_ORDER: { name: string; displayName: string }[] = [
  { name: "data_ingestion", displayName: "Data Ingestion" },
  { name: "simulation_engine", displayName: "Simulation Engine" },
  { name: "citizen_proxy", displayName: "Citizen Proxy" },
  { name: "policy_testing", displayName: "Policy Testing" },
  { name: "impact_analysis", displayName: "Impact Analysis" },
  { name: "recommendation", displayName: "Recommendation" },
];

const initialAgents = (): AgentStatus[] =>
  AGENT_ORDER.map((a) => ({ ...a, status: "pending" }));

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export default function Home() {
  const [presets, setPresets] = useState<PolicyPreset[]>([]);
  const [baselineGeoJSON, setBaselineGeoJSON] = useState<GeoJSONFeatureCollection | null>(null);
  const [modifiedGeoJSON, setModifiedGeoJSON] = useState<GeoJSONFeatureCollection | null>(null);
  const [baselineMetrics, setBaselineMetrics] = useState<BaselineMetrics | null>(null);
  const [impactScores, setImpactScores] = useState<ImpactScores | null>(null);
  const [recommendations, setRecommendations] = useState<string | null>(null);
  const [agents, setAgents] = useState<AgentStatus[]>(initialAgents());
  const [isLoading, setIsLoading] = useState(false);
  const [showModified, setShowModified] = useState(false);
  const [activeTab, setActiveTab] = useState<"metrics" | "report">("metrics");
  const [currentPolicy, setCurrentPolicy] = useState<string>("");
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    fetchPresets().then(setPresets).catch(console.error);
    fetchKochiGeoJSON().then(setBaselineGeoJSON).catch(console.error);
    fetchBaselineMetrics().then(setBaselineMetrics).catch(console.error);
  }, []);

  const runSimulation = useCallback(
    async (policy: string) => {
      if (isLoading) return;

      setIsLoading(true);
      setCurrentPolicy(policy);
      setAgents(initialAgents());
      setImpactScores(null);
      setRecommendations(null);
      setModifiedGeoJSON(null);
      setShowModified(false);
      setActiveTab("metrics");

      if (esRef.current) esRef.current.close();

      try {
        const { job_id } = await startSimulation(policy);
        const es = new EventSource(`${API_BASE}/simulate/${job_id}/stream`);
        esRef.current = es;

        es.onmessage = (e) => {
          const event: StreamEvent = JSON.parse(e.data);

          if (event.type === "agent_complete" && event.agent) {
            const completedIdx = AGENT_ORDER.findIndex((o) => o.name === event.agent);
            setAgents((prev) =>
              prev.map((a, i) => {
                if (a.name === event.agent) {
                  return {
                    ...a,
                    status: event.status === "error" ? "error" : "completed",
                    message: event.message,
                  };
                }
                if (i === completedIdx + 1) {
                  return { ...a, status: "running" };
                }
                return a;
              })
            );
          }

          if (event.type === "data" && event.key === "impact_scores") {
            setImpactScores(event.data as ImpactScores);
          }

          if (event.type === "complete") {
            fetch(`${API_BASE}/simulate/${job_id}/result`)
              .then((r) => r.json())
              .then((result) => {
                if (result.result) {
                  setImpactScores(result.result.impact_scores || null);
                  setRecommendations(result.result.recommendations || null);
                }
              })
              .catch(console.error)
              .finally(() => {
                setIsLoading(false);
                setShowModified(true);
                setActiveTab("report");
                es.close();
              });
          }

          if (event.type === "error") {
            setIsLoading(false);
            es.close();
          }
        };

        es.onerror = () => {
          setIsLoading(false);
          es.close();
        };

        setAgents((prev) =>
          prev.map((a, i) => (i === 0 ? { ...a, status: "running" } : a))
        );
      } catch (err) {
        console.error(err);
        setIsLoading(false);
      }
    },
    [isLoading]
  );

  return (
    <div className="h-screen flex flex-col bg-gray-50 overflow-hidden">
      {/* Header */}
      <header className="bg-gray-900 text-white px-6 py-3 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-500 flex items-center justify-center text-sm font-bold">
            SC
          </div>
          <div>
            <div className="font-bold text-sm tracking-wide">SimCity AI</div>
            <div className="text-xs text-gray-400">Kochi Digital Twin — Policy Simulator</div>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {baselineMetrics && (
            <div className="hidden md:flex items-center gap-4 text-xs text-gray-400">
              <span>{baselineMetrics.total_nodes.toLocaleString()} intersections</span>
              <span>{baselineMetrics.total_edges.toLocaleString()} road segments</span>
              <span>
                {(baselineMetrics.avg_congestion_ratio * 100).toFixed(0)}% avg congestion
              </span>
            </div>
          )}
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs text-gray-400">Live</span>
          </div>
        </div>
      </header>

      {/* Main 3-column layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar */}
        <aside className="w-72 flex-shrink-0 bg-white border-r border-gray-100 flex flex-col overflow-y-auto">
          <div className="p-4 flex flex-col gap-6">
            <PolicyInput presets={presets} onSimulate={runSimulation} isLoading={isLoading} />
            <div className="border-t border-gray-100 pt-4">
              <AgentTimeline agents={agents} />
            </div>
          </div>
        </aside>

        {/* Center: Map */}
        <main className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 p-3 min-h-0">
            <CityMap
              baselineGeoJSON={baselineGeoJSON}
              modifiedGeoJSON={modifiedGeoJSON}
              showModified={showModified}
            />
          </div>

          {/* Before/After toggle */}
          {modifiedGeoJSON && (
            <div className="px-3 pb-2 flex items-center gap-3 flex-shrink-0">
              <span className="text-xs text-gray-500">View:</span>
              <button
                onClick={() => setShowModified(false)}
                className={`text-xs px-3 py-1 rounded-full border transition-all ${
                  !showModified
                    ? "bg-indigo-600 text-white border-indigo-600"
                    : "border-gray-200 text-gray-600 hover:border-gray-300"
                }`}
              >
                Before policy
              </button>
              <button
                onClick={() => setShowModified(true)}
                className={`text-xs px-3 py-1 rounded-full border transition-all ${
                  showModified
                    ? "bg-indigo-600 text-white border-indigo-600"
                    : "border-gray-200 text-gray-600 hover:border-gray-300"
                }`}
              >
                After policy
              </button>
              <span className="text-xs text-gray-400 italic truncate max-w-xs">
                {currentPolicy.slice(0, 60)}
                {currentPolicy.length > 60 ? "…" : ""}
              </span>
            </div>
          )}
        </main>

        {/* Right sidebar */}
        <aside className="w-80 flex-shrink-0 bg-white border-l border-gray-100 flex flex-col overflow-hidden">
          <div className="flex border-b border-gray-100 flex-shrink-0">
            <button
              onClick={() => setActiveTab("metrics")}
              className={`flex-1 py-3 text-xs font-semibold transition-colors ${
                activeTab === "metrics"
                  ? "text-indigo-600 border-b-2 border-indigo-600"
                  : "text-gray-400 hover:text-gray-600"
              }`}
            >
              Impact Metrics
            </button>
            <button
              onClick={() => setActiveTab("report")}
              className={`flex-1 py-3 text-xs font-semibold transition-colors ${
                activeTab === "report"
                  ? "text-indigo-600 border-b-2 border-indigo-600"
                  : "text-gray-400 hover:text-gray-600"
              }`}
            >
              AI Report
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            {activeTab === "metrics" && (
              <ImpactMetrics baseline={baselineMetrics} impact={impactScores} />
            )}
            {activeTab === "report" && (
              <ReportPanel recommendations={recommendations} isLoading={isLoading} />
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
