"use client";
import { AgentStatus } from "@/lib/types";

interface Props {
  agents: AgentStatus[];
}

const statusIcon = {
  pending: <span className="w-2.5 h-2.5 rounded-full bg-gray-300 inline-block" />,
  running: (
    <span className="w-2.5 h-2.5 rounded-full bg-indigo-400 inline-block animate-pulse" />
  ),
  completed: (
    <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 inline-block" />
  ),
  error: <span className="w-2.5 h-2.5 rounded-full bg-red-400 inline-block" />,
};

const statusLabel = {
  pending: "text-gray-400",
  running: "text-indigo-600 font-semibold",
  completed: "text-emerald-600",
  error: "text-red-500",
};

export default function AgentTimeline({ agents }: Props) {
  return (
    <div className="flex flex-col gap-1">
      <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wider mb-2">
        Agent Pipeline
      </h2>
      <div className="relative">
        {/* Connector line */}
        <div className="absolute left-[5px] top-3 bottom-3 w-px bg-gray-200" />

        <div className="flex flex-col gap-3">
          {agents.map((agent, i) => (
            <div key={agent.name} className="flex items-start gap-3 relative">
              <div className="mt-0.5 z-10 bg-white">{statusIcon[agent.status]}</div>
              <div className="flex-1 min-w-0">
                <div className={`text-sm ${statusLabel[agent.status]}`}>
                  {agent.displayName}
                </div>
                {agent.message && agent.status !== "pending" && (
                  <div className="text-xs text-gray-400 mt-0.5 truncate leading-relaxed">
                    {agent.message}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
