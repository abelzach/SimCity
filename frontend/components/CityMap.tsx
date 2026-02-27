"use client";
import { useEffect, useRef } from "react";
import { GeoJSONFeatureCollection } from "@/lib/types";

interface Props {
  baselineGeoJSON: GeoJSONFeatureCollection | null;
  modifiedGeoJSON: GeoJSONFeatureCollection | null;
  showModified: boolean;
}

const congestionColors: Record<string, string> = {
  free: "#22c55e",
  moderate: "#eab308",
  heavy: "#f97316",
  severe: "#ef4444",
  closed: "#6366f1",
};

const congestionWeights: Record<string, number> = {
  free: 2,
  moderate: 2.5,
  heavy: 3,
  severe: 3.5,
  closed: 2,
};

export default function CityMap({ baselineGeoJSON, modifiedGeoJSON, showModified }: Props) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<unknown>(null);
  const baselineLayerRef = useRef<unknown>(null);
  const modifiedLayerRef = useRef<unknown>(null);
  // Synchronous guard prevents StrictMode double-init before the async IIFE resolves
  const initGuardRef = useRef(false);

  useEffect(() => {
    if (typeof window === "undefined" || !mapRef.current) return;
    // Check both the ref and the Leaflet container flag (_leaflet_id is set synchronously by L.map)
    if (initGuardRef.current || (mapRef.current as unknown as Record<string, unknown>)["_leaflet_id"]) return;
    initGuardRef.current = true;

    (async () => {
      const L = (await import("leaflet")).default;

      // Guard again after await in case cleanup ran during the import
      if (!mapRef.current || mapInstanceRef.current) return;

      const map = L.map(mapRef.current, {
        center: [9.9816, 76.2999],
        zoom: 13,
        zoomControl: true,
      });

      L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
        attribution: '© <a href="https://carto.com/">CARTO</a>',
        subdomains: "abcd",
        maxZoom: 19,
      }).addTo(map);

      mapInstanceRef.current = map;
    })();

    return () => {
      initGuardRef.current = false;
      if (mapInstanceRef.current) {
        (mapInstanceRef.current as { remove: () => void }).remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  // Update baseline layer
  useEffect(() => {
    if (!mapInstanceRef.current || !baselineGeoJSON) return;

    (async () => {
      const L = (await import("leaflet")).default;
      const map = mapInstanceRef.current as { addLayer: (l: unknown) => void; removeLayer: (l: unknown) => void };

      if (baselineLayerRef.current) {
        map.removeLayer(baselineLayerRef.current);
      }

      const layer = L.geoJSON(baselineGeoJSON as Parameters<typeof L.geoJSON>[0], {
        style: (feature) => {
          const level = feature?.properties?.congestion_level || "moderate";
          return {
            color: congestionColors[level] || "#888",
            weight: congestionWeights[level] || 2,
            opacity: showModified ? 0.25 : 0.85,
          };
        },
        onEachFeature: (feature, leafletLayer) => {
          const p = feature.properties;
          leafletLayer.bindTooltip(
            `<div class="text-xs">
              <strong>${p.name || p.highway || "Road"}</strong><br/>
              Congestion: ${(p.congestion_ratio * 100).toFixed(0)}%<br/>
              Flow: ${p.baseline_flow.toLocaleString()} veh/hr
            </div>`,
            { sticky: true }
          );
        },
      });

      layer.addTo(map as Parameters<typeof layer.addTo>[0]);
      baselineLayerRef.current = layer;
    })();
  }, [baselineGeoJSON, showModified]);

  // Update modified layer
  useEffect(() => {
    if (!mapInstanceRef.current || !modifiedGeoJSON) return;

    (async () => {
      const L = (await import("leaflet")).default;
      const map = mapInstanceRef.current as { addLayer: (l: unknown) => void; removeLayer: (l: unknown) => void };

      if (modifiedLayerRef.current) {
        map.removeLayer(modifiedLayerRef.current);
      }

      if (!showModified) return;

      // Only render edges that changed
      const changedFeatures = {
        ...modifiedGeoJSON,
        features: modifiedGeoJSON.features.filter(
          (f) => f.properties.is_modified || f.properties.is_closed
        ),
      };

      const layer = L.geoJSON(changedFeatures as Parameters<typeof L.geoJSON>[0], {
        style: (feature) => {
          const isClosed = feature?.properties?.is_closed;
          if (isClosed) {
            return { color: congestionColors.closed, weight: 4, opacity: 0.95, dashArray: "6,4" };
          }
          const level = feature?.properties?.congestion_level || "moderate";
          return {
            color: congestionColors[level] || "#888",
            weight: congestionWeights[level] + 1,
            opacity: 0.95,
          };
        },
        onEachFeature: (feature, leafletLayer) => {
          const p = feature.properties;
          const status = p.is_closed ? "CLOSED" : `Congestion: ${(p.congestion_ratio * 100).toFixed(0)}%`;
          leafletLayer.bindTooltip(
            `<div class="text-xs">
              <strong>${p.name || p.highway || "Road"}</strong><br/>
              ${status}<br/>
              <em>Modified by policy</em>
            </div>`,
            { sticky: true }
          );
        },
      });

      layer.addTo(map as Parameters<typeof layer.addTo>[0]);
      modifiedLayerRef.current = layer;
    })();
  }, [modifiedGeoJSON, showModified]);

  return (
    <div className="relative w-full h-full">
      <div ref={mapRef} className="w-full h-full rounded-xl overflow-hidden" />

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-black/70 text-white rounded-lg p-3 text-xs z-[1000] backdrop-blur-sm">
        <div className="font-semibold mb-2 text-gray-300">Congestion Level</div>
        {Object.entries(congestionColors).map(([level, color]) => (
          <div key={level} className="flex items-center gap-2 mb-1">
            <div className="w-6 h-1.5 rounded-full" style={{ backgroundColor: color }} />
            <span className="capitalize text-gray-300">{level}</span>
          </div>
        ))}
      </div>

      {/* Loading overlay */}
      {!baselineGeoJSON && (
        <div className="absolute inset-0 bg-gray-900 rounded-xl flex items-center justify-center z-[1000]">
          <div className="text-center text-white">
            <div className="animate-spin h-8 w-8 border-2 border-indigo-400 border-t-transparent rounded-full mx-auto mb-3" />
            <div className="text-sm">Loading Kochi road network...</div>
          </div>
        </div>
      )}
    </div>
  );
}
