import React, { useState, useEffect, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Map from "react-map-gl/maplibre";
import DeckGL from "@deck.gl/react";
import { PathLayer, ScatterplotLayer } from "deck.gl";
import { PathStyleExtension } from "@deck.gl/extensions";
import "maplibre-gl/dist/maplibre-gl.css";
import axios from "axios";

const API = "http://localhost:8000";

// --- City definitions with business archetype mapping ---
const CITIES = [
  { name: "Mumbai",    lat: 19.076, lng: 72.877, type: "port",       businesses: ["Textiles", "Pharma"], color: "#4488ff" },
  { name: "Delhi",     lat: 28.613, lng: 77.209, type: "hub",        businesses: ["Agriculture", "Auto Parts"], color: "#00cc44" },
  { name: "Bangalore", lat: 12.971, lng: 77.594, type: "hub",        businesses: ["Pharma", "Electronics"], color: "#00cc44" },
  { name: "Chennai",   lat: 13.083, lng: 80.270, type: "port",       businesses: ["Auto Parts", "Textiles"], color: "#4488ff" },
  { name: "Kolkata",   lat: 22.572, lng: 88.363, type: "port",       businesses: ["Jute", "Steel"], color: "#4488ff" },
  { name: "Surat",     lat: 21.170, lng: 72.831, type: "industrial", businesses: ["Diamonds", "Textiles"], color: "#ff9900" },
  { name: "Pune",      lat: 18.520, lng: 73.856, type: "industrial", businesses: ["Auto Parts", "Pharma"], color: "#ff9900" },
  { name: "Ahmedabad", lat: 23.022, lng: 72.571, type: "industrial", businesses: ["Textiles", "Chemicals"], color: "#ff9900" },
  { name: "Hyderabad", lat: 17.385, lng: 78.486, type: "hub",        businesses: ["Pharma", "IT"], color: "#00cc44" },
  { name: "Nagpur",    lat: 21.145, lng: 79.088, type: "hub",        businesses: ["Agriculture", "Logistics"], color: "#00cc44" },
  { name: "Jaipur",    lat: 26.912, lng: 75.787, type: "industrial", businesses: ["Textiles", "Gems"], color: "#ff9900" },
  { name: "Kochi",     lat: 9.931,  lng: 76.267, type: "port",       businesses: ["Spices", "Fisheries"], color: "#4488ff" },
];

// --- Highway corridors ---
const CORRIDORS = [
  { id: "NH48", name: "Mumbai–Delhi",          from: "Mumbai",    to: "Delhi",     risk: 0.72, color: "#ff4444", via: ["Ahmedabad", "Jaipur"] },
  { id: "NH47", name: "Pune–Bangalore",        from: "Pune",      to: "Bangalore", risk: 0.45, color: "#ff9900", via: [] },
  { id: "NH44", name: "Srinagar–Kanyakumari",  from: "Delhi",     to: "Chennai",   risk: 0.30, color: "#ffcc00", via: ["Nagpur", "Hyderabad"] },
  { id: "NH19", name: "Delhi–Kolkata",         from: "Delhi",     to: "Kolkata",   risk: 0.15, color: "#00cc44", via: ["Nagpur"] },
  { id: "NH16", name: "Kolkata–Chennai",       from: "Kolkata",   to: "Chennai",   risk: 0.20, color: "#4488ff", via: ["Hyderabad"] },
  { id: "NH66", name: "Mumbai–Kochi",          from: "Mumbai",    to: "Kochi",     risk: 0.25, color: "#bb44ff", via: [] },
];

// Helper to convert hex out of #000000 format to RGB array for deck.gl
function hexToRgb(hex) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? [
    parseInt(result[1], 16),
    parseInt(result[2], 16),
    parseInt(result[3], 16)
  ] : [255, 255, 255];
}

export default function IndiaMap({ onBack, alerts, users }) {
  const [selectedCorridor, setSelectedCorridor] = useState(null);
  const [selectedCity, setSelectedCity] = useState(null);
  const [localAlerts, setLocalAlerts] = useState(alerts || []);
  const [time, setTime] = useState(0);

  // Animate the flow lines along the paths
  useEffect(() => {
    let raf;
    const animate = () => {
      setTime(t => (t + 1) % 100);
      raf = requestAnimationFrame(animate);
    };
    raf = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(raf);
  }, []);

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const res = await axios.get(`${API}/alerts`);
        setLocalAlerts(res.data.alerts || []);
      } catch {/* ignore */}
    };
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 15000);
    return () => clearInterval(interval);
  }, []);

  // Prepare path data for Deck.GL
  const pathData = useMemo(() => {
    return CORRIDORS.map(corridor => {
      const cities = [corridor.from, ...(corridor.via || []), corridor.to];
      const path = cities.map(name => {
        const city = CITIES.find(c => c.name === name);
        return city ? [city.lng, city.lat] : null;
      }).filter(Boolean);

      return {
        ...corridor,
        path,
        rgbColor: hexToRgb(corridor.color)
      };
    });
  }, []);

  // Prepare city data for Deck.GL
  const cityNodes = useMemo(() => {
    return CITIES.map(city => {
      const hasHighRisk = localAlerts.some(a => {
        return CORRIDORS.filter(c => c.risk > 0.3).some(c =>
          c.from === city.name || c.to === city.name || (c.via || []).includes(city.name)
        );
      });
      return {
        ...city,
        coordinates: [city.lng, city.lat],
        rgbColor: hexToRgb(city.color),
        radiusSize: city.type === "port" ? 18000 : city.type === "hub" ? 15000 : 12000,
        hasPulse: hasHighRisk,
      };
    });
  }, [localAlerts]);

  const layers = [
    // Base solid lines
    new PathLayer({
      id: 'corridor-path-base',
      data: pathData,
      pickable: true,
      widthScale: 1,
      widthMinPixels: 2,
      getPath: d => d.path,
      getColor: d => {
        const rgb = d.rgbColor;
        const opacity = (!selectedCorridor || selectedCorridor.id === d.id) ? 180 : 40;
        return [...rgb, opacity];
      },
      getWidth: d => (!selectedCorridor || selectedCorridor.id === d.id) ? 4000 : 2000,
      onClick: ({ object }) => handleCorridorClick(object),
      autoHighlight: true,
      highlightColor: [255, 255, 255, 120]
    }),
    
    // Animated glowing overlay (dashed lines)
    new PathLayer({
      id: 'corridor-path-animated',
      data: pathData.filter(d => !selectedCorridor || selectedCorridor.id === d.id),
      pickable: false,
      widthScale: 1,
      widthMinPixels: 3,
      getPath: d => d.path,
      getColor: d => [...d.rgbColor, 255],
      getWidth: 4000,
      getDashArray: d => [20, 40],
      dashJustified: false,
      extensions: [new PathStyleExtension({dash: true})],
      updateTriggers: {
        // DeckGL animations usually need a custom shader for dash offset 
        // Emulating here by triggering rerenders with 'time' is hacky but visually somewhat effective.
      }
    }),

    // City Drop shadow / pulse 
    new ScatterplotLayer({
      id: 'city-nodes-pulse',
      data: cityNodes.filter(c => c.hasPulse),
      pickable: false,
      opacity: 0.1,
      stroked: false,
      filled: true,
      radiusScale: 1 + Math.sin(time * 0.1) * 0.5,
      getRadius: d => d.radiusSize * 2.5,
      getPosition: d => d.coordinates,
      getFillColor: d => [...d.rgbColor, 100],
      updateTriggers: { radiusScale: [time] }
    }),

    // City primary node
    new ScatterplotLayer({
      id: 'city-nodes',
      data: cityNodes,
      pickable: true,
      opacity: 0.9,
      stroked: true,
      filled: true,
      radiusScale: 1,
      radiusMinPixels: 4,
      radiusMaxPixels: 15,
      lineWidthMinPixels: 1.5,
      getPosition: d => d.coordinates,
      getRadius: d => d.radiusSize,
      getFillColor: d => (selectedCity?.name === d.name ? [255, 255, 255] : [13, 21, 48]),
      getLineColor: d => d.rgbColor,
      onClick: ({ object }) => handleCityClick(object),
      autoHighlight: true,
      highlightColor: [255, 255, 255, 200]
    }),
  ];

  const handleCorridorClick = (corridor) => {
    setSelectedCorridor(prev => prev?.id === corridor.id ? null : corridor);
    setSelectedCity(null);
  };

  const handleCityClick = (city) => {
    setSelectedCity(prev => prev?.name === city.name ? null : city);
    setSelectedCorridor(null);
  };

  // Stats
  const totalBusinesses = users?.length || 3;
  const activeThreats = CORRIDORS.filter(c => c.risk > 0.3).length;
  const highRisk = CORRIDORS.filter(c => c.risk > 0.6).length;

  const cityCorridors = selectedCity
    ? CORRIDORS.filter(c => c.from === selectedCity.name || c.to === selectedCity.name || (c.via||[]).includes(selectedCity.name))
    : [];

  return (
    <motion.div
      initial={{ opacity: 0, scale: 1.08 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      style={{
        position: "fixed", inset: 0,
        background: "#040810",
        zIndex: 100,
        display: "flex",
        fontFamily: "IBM Plex Mono, monospace",
        color: "#e0e6f0",
        overflow: "hidden",
      }}
    >
      {/* ─── LEFT SIDEBAR ─── */}
      <div style={{
        width: 280,
        background: "#06090faa",
        backdropFilter: "blur(20px)",
        borderRight: "1px solid #0d1530",
        display: "flex",
        flexDirection: "column",
        padding: "24px 16px",
        zIndex: 10,
        boxShadow: "10px 0 30px rgba(0,0,0,0.5)"
      }}>
        <motion.button
          whileHover={{ x: -3 }}
          onClick={onBack}
          style={{
            display: "flex", alignItems: "center", gap: 8,
            background: "#ffffff08",
            border: "1px solid #1a2040",
            color: "#4488ff", borderRadius: 8,
            padding: "8px 12px", cursor: "pointer",
            fontSize: 11, letterSpacing: 2,
            marginBottom: 24,
          }}
        >
          &larr; GLOBE VIEW
        </motion.button>

        <div style={{ fontSize: 10, color: "#334466", letterSpacing: 3, marginBottom: 6 }}>INDIA INTERACTIVE</div>
        <div style={{ fontSize: 18, fontWeight: 700, fontFamily: "Syne, sans-serif", color: "#e0e6f0", marginBottom: 20 }}>
          Live Street Map
        </div>

        {/* Stats */}
        {[
          { label: "Corridors Active",    value: CORRIDORS.length,  color: "#4488ff" },
          { label: "Active Threats",      value: activeThreats,     color: "#ff4444" },
          { label: "High Risk Corridors", value: highRisk,          color: "#ff4444" },
          { label: "Cities Monitored",    value: CITIES.length,     color: "#00cc44" },
          { label: "Businesses Online",   value: totalBusinesses,   color: "#ff9900" },
        ].map(s => (
          <div key={s.label} style={{
            display: "flex", justifyContent: "space-between",
            padding: "10px 12px", marginBottom: 4,
            background: "#ffffff04", borderRadius: 6,
            border: "1px solid #0d1530",
          }}>
            <span style={{ fontSize: 10, color: "#6677aa" }}>{s.label}</span>
            <span style={{ fontSize: 14, fontWeight: 700, color: s.color, fontFamily: "Syne, sans-serif" }}>{s.value}</span>
          </div>
        ))}

        <div style={{ marginTop: 20, fontSize: 10, color: "#334466", letterSpacing: 2, marginBottom: 10 }}>CORRIDOR LEGEND</div>
        {CORRIDORS.map(c => (
          <motion.div
            key={c.id}
            whileHover={{ x: 4 }}
            onClick={() => handleCorridorClick(c)}
            style={{
              display: "flex", alignItems: "center", gap: 10,
              padding: "8px 10px", borderRadius: 6, marginBottom: 4,
              background: selectedCorridor?.id === c.id ? `${c.color}18` : "#ffffff04",
              border: `1px solid ${selectedCorridor?.id === c.id ? c.color + "66" : "#0d1530"}`,
              cursor: "pointer",
            }}
          >
            <div style={{ width: 28, height: 3, borderRadius: 2, background: c.color, opacity: 0.8 }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 11, color: "#e0e6f0", fontWeight: 600 }}>{c.id}</div>
              <div style={{ fontSize: 9, color: "#6677aa" }}>{c.name}</div>
            </div>
            <div style={{ fontSize: 11, fontWeight: 700, color: c.color }}>
              {(c.risk * 100).toFixed(0)}%
            </div>
          </motion.div>
        ))}
        
        <div style={{ marginTop: "auto", fontSize: 10, color: "#4488ff", fontStyle: "italic", textAlign: "center" }}>
          Zoom and pan standard map features<br/> to access real streets.
        </div>
      </div>

      {/* ─── CENTER MAP ─── */}
      <div style={{ flex: 1, position: "relative" }}>
        {/* Header Overlay */}
        <div style={{
          position: "absolute", top: 0, left: 0, right: 0, zIndex: 5,
          padding: "18px 28px",
          pointerEvents: "none",
          background: "linear-gradient(to bottom, #040810ee, transparent)",
          display: "flex", alignItems: "center", justifyContent: "space-between",
        }}>
          <div>
            <div style={{ fontFamily: "Syne, sans-serif", fontSize: 18, fontWeight: 800, letterSpacing: 4, color: "#e0e6f0" }}>
              TACTICAL STREET LAYER
            </div>
            <div style={{ fontSize: 10, color: "#4488ff", letterSpacing: 3 }}>
              LIVE SUPPLY MESH &middot; {CORRIDORS.length} HIGHWAYS
            </div>
          </div>
        </div>

        {/* Real Interactive Map using react-map-gl and maplibre */}
        <DeckGL
          initialViewState={{
            longitude: 78.9629,
            latitude: 20.5937,
            zoom: 4.5,
            pitch: 30,
            bearing: 0
          }}
          controller={true}
          layers={layers}
          getTooltip={({object}) => object && (object.businesses ? `${object.name} (${object.type})` : `${object.name} Highway`)}
        >
          <Map
            mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
            reuseMaps
            preventStyleDiffing={true}
          />
        </DeckGL>

        {/* Bottom Alert Strip */}
        {localAlerts.length > 0 && (
          <div style={{
            position: "absolute", bottom: 0, left: 0, right: 0,
            padding: "12px 24px",
            background: "linear-gradient(to top, #040810ee, transparent)",
            display: "flex", gap: 8, alignItems: "center", overflowX: "auto",
            zIndex: 5,
          }}>
            <span style={{ fontSize: 9, color: "#334466", letterSpacing: 2, flexShrink: 0 }}>LIVE ALERTS</span>
            {localAlerts.map(a => {
              const sev = a.severity;
              const c = sev === "HIGH" ? "#ff4444" : sev === "MEDIUM" ? "#ff9900" : "#00cc44";
              return (
                <motion.div
                  key={a.alert_id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  style={{
                    display: "flex", alignItems: "center", gap: 8,
                    padding: "6px 12px", borderRadius: 20,
                    background: `${c}11`, border: `1px solid ${c}44`,
                    flexShrink: 0,
                  }}
                >
                  <div style={{ width: 6, height: 6, borderRadius: "50%", background: c }} />
                  <span style={{ fontSize: 10, color: "#aabbcc" }}>{a.user_name}</span>
                  <span style={{ fontSize: 10, color: c, fontWeight: 700 }}>{a.highway}</span>
                  <span style={{ fontSize: 10, color: "#6677aa" }}>&#8377;{a.counterfactual_cost_inr?.toLocaleString("en-IN")}</span>
                </motion.div>
              );
            })}
          </div>
        )}
      </div>

      {/* ─── RIGHT DETAILS PANEL ─── */}
      <AnimatePresence mode="wait">
        {(selectedCorridor || selectedCity) && (
          <motion.div
            key={selectedCorridor?.id || selectedCity?.name}
            initial={{ opacity: 0, x: 60 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 60 }}
            transition={{ type: "spring", stiffness: 200, damping: 24 }}
            style={{
              width: 320,
              background: "#06090faa",
              backdropFilter: "blur(20px)",
              borderLeft: "1px solid #0d1530",
              display: "flex", flexDirection: "column",
              padding: 24, gap: 12, zIndex: 10,
              overflowY: "auto",
              boxShadow: "-10px 0 30px rgba(0,0,0,0.5)"
            }}
          >
            {/* ── Corridor detail ── */}
            {selectedCorridor && (
              <>
                <div style={{ fontSize: 10, color: "#334466", letterSpacing: 3 }}>CORRIDOR DETAIL</div>
                <div style={{ fontSize: 24, fontWeight: 700, fontFamily: "Syne, sans-serif", color: selectedCorridor.color }}>
                  {selectedCorridor.id}
                </div>
                <div style={{ fontSize: 12, color: "#6677aa" }}>{selectedCorridor.name}</div>

                <div style={{ marginTop: 8 }}>
                  <div style={{ fontSize: 10, color: "#334466", marginBottom: 6, letterSpacing: 2 }}>RISK LEVEL</div>
                  <div style={{ height: 10, background: "#0d1530", borderRadius: 5, overflow: "hidden" }}>
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${selectedCorridor.risk * 100}%` }}
                      transition={{ duration: 0.8, ease: "easeOut" }}
                      style={{ height: "100%", background: selectedCorridor.color, borderRadius: 5 }}
                    />
                  </div>
                  <div style={{ fontSize: 28, fontWeight: 700, color: selectedCorridor.color, fontFamily: "Syne, sans-serif", marginTop: 8 }}>
                    {(selectedCorridor.risk * 100).toFixed(0)}%
                  </div>
                </div>

                <div style={{ fontSize: 10, color: "#334466", letterSpacing: 2, marginTop: 12 }}>CITIES ON ROUTE</div>
                {[selectedCorridor.from, ...(selectedCorridor.via || []), selectedCorridor.to].map(cityName => {
                  const city = CITIES.find(c => c.name === cityName);
                  if (!city) return null;
                  return (
                    <div key={cityName} style={{
                      display: "flex", alignItems: "center", gap: 10,
                      padding: "10px 12px", background: "#ffffff05",
                      borderRadius: 6, border: "1px solid #0d1530",
                    }}>
                      <div style={{ width: 8, height: 8, borderRadius: "50%", background: city.color }} />
                      <div>
                        <div style={{ fontSize: 12, color: "#e0e6f0", fontWeight: 600 }}>{city.name}</div>
                        <div style={{ fontSize: 9, color: "#6677aa" }}>{city.type.toUpperCase()}</div>
                      </div>
                    </div>
                  );
                })}
              </>
            )}

            {/* ── City detail ── */}
            {selectedCity && !selectedCorridor && (
              <>
                <div style={{ fontSize: 10, color: "#334466", letterSpacing: 3 }}>CITY INTELLIGENCE</div>
                <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 4 }}>
                  <div style={{
                    width: 48, height: 48, borderRadius: "50%",
                    background: `${selectedCity.color}22`,
                    border: `2px solid ${selectedCity.color}`,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    fontSize: 20, fontWeight: 700, color: selectedCity.color,
                    fontFamily: "Syne, sans-serif",
                  }}>
                    {selectedCity.name.charAt(0)}
                  </div>
                  <div>
                    <div style={{ fontSize: 20, fontWeight: 700, fontFamily: "Syne, sans-serif", color: "#e0e6f0" }}>
                      {selectedCity.name}
                    </div>
                    <div style={{ fontSize: 10, color: selectedCity.color, letterSpacing: 2, marginTop: 4 }}>
                      {selectedCity.type.toUpperCase()}
                    </div>
                  </div>
                </div>

                <div style={{ fontSize: 10, color: "#334466", letterSpacing: 2, marginTop: 16 }}>INDUSTRIES</div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  {selectedCity.businesses.map(b => (
                    <div key={b} style={{
                      padding: "6px 12px", borderRadius: 20,
                      background: `${selectedCity.color}18`,
                      border: `1px solid ${selectedCity.color}44`,
                      fontSize: 11, color: selectedCity.color,
                    }}>{b}</div>
                  ))}
                </div>

                <div style={{ fontSize: 10, color: "#334466", letterSpacing: 2, marginTop: 16 }}>CONNECTED CORRIDORS</div>
                {cityCorridors.map(c => (
                  <div key={c.id} style={{
                    display: "flex", alignItems: "center", gap: 10,
                    padding: "10px 12px", background: "#ffffff05",
                    borderRadius: 6, border: `1px solid ${c.color}33`,
                    cursor: "pointer",
                  }} onClick={() => handleCorridorClick(c)}>
                    <div style={{ width: 24, height: 4, background: c.color, borderRadius: 2 }} />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 12, color: "#e0e6f0", fontWeight: 600 }}>{c.id}</div>
                      <div style={{ fontSize: 10, color: "#6677aa", marginTop: 2 }}>{c.name}</div>
                    </div>
                    <div style={{ fontSize: 14, color: c.color, fontWeight: 700 }}>{(c.risk * 100).toFixed(0)}%</div>
                  </div>
                ))}
                
                {users && users.filter(u =>
                  u.active_shipments?.some(s =>
                    cityCorridors.some(c => c.from === s.from || c.to === s.to || c.from === s.to || c.to === s.from)
                  )
                ).length > 0 && (
                  <>
                    <div style={{ fontSize: 10, color: "#334466", letterSpacing: 2, marginTop: 16 }}>BUSINESSES HERE</div>
                    {users.filter(u =>
                      u.active_shipments?.some(s =>
                        cityCorridors.some(c => c.from === s.from || c.to === s.to || c.from === s.to || c.to === s.from)
                      )
                    ).map(u => (
                      <div key={u.user_id} style={{
                        padding: "12px 14px",
                        background: "#ffffff05",
                        border: "1px solid #0d1530",
                        borderRadius: 8,
                        marginTop: 8
                      }}>
                        <div style={{ fontSize: 14, fontWeight: 700, color: "#e0e6f0" }}>{u.name}</div>
                        <div style={{ fontSize: 11, color: "#6677aa", marginTop: 4 }}>{u.business}</div>
                      </div>
                    ))}
                  </>
                )}
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
