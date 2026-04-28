import { useEffect, useRef, useState, Suspense, useCallback } from "react";
import { Canvas, useFrame, useLoader } from "@react-three/fiber";
import { OrbitControls, Stars } from "@react-three/drei";
import { motion, AnimatePresence } from "framer-motion";
import * as THREE from "three";
import axios from "axios";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const CORRIDORS_BASE = [
  { id: "NH48", name: "Mumbai–Delhi", cities: [[19.076, 72.877], [28.613, 77.209]] },
  { id: "NH47", name: "Pune–Bangalore", cities: [[18.520, 73.856], [12.971, 77.594]] },
  { id: "NH44", name: "Srinagar–Kanyakumari", cities: [[34.083, 74.797], [8.087, 77.552]] },
  { id: "NH19", name: "Delhi–Kolkata", cities: [[28.613, 77.209], [22.572, 88.363]] },
  { id: "NH16", name: "Kolkata–Chennai", cities: [[22.572, 88.363], [13.083, 80.270]] },
  { id: "NH27", name: "Ahmedabad–Silchar", cities: [[23.022, 72.571], [24.817, 92.797]] },
];

const BUSINESS_TYPES = [
  { value: "textile_north", label: "Textile Manufacturer", icon: "🧵", region: "North India", highway: "NH48" },
  { value: "pharma_west", label: "Pharma Distributor", icon: "💊", region: "West India", highway: "NH47" },
  { value: "agri_south", label: "Agri Cooperative", icon: "🌾", region: "South India", highway: "NH44" },
  { value: "auto_central", label: "Auto Parts Mfg", icon: "⚙️", region: "Central India", highway: "NH44" },
  { value: "ecommerce_east", label: "E-commerce Seller", icon: "📦", region: "East India", highway: "NH19" },
];

const LANGUAGES = [
  { value: "hindi", label: "हिंदी" },
  { value: "kannada", label: "ಕನ್ನಡ" },
  { value: "marathi", label: "मराठी" },
  { value: "english", label: "English" },
];

const COMPONENT_COLORS = {
  weather_ml: "#4488ff",
  news_sentiment: "#ff9900",
  port_congestion: "#ff4444",
  commodity_volatility: "#00cc44",
};
const COMPONENT_ICONS = {
  weather_ml: "🌧️",
  news_sentiment: "📰",
  port_congestion: "⚓",
  commodity_volatility: "📦",
};

function riskColor(r) {
  return r > 0.6 ? "#ff4444" : r > 0.35 ? "#ff9900" : "#00cc44";
}
function latLngToVec3(lat, lng, radius = 2.0) {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lng + 180) * (Math.PI / 180);
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta)
  );
}

// ── 3D ────────────────────────────────────────────────────────────
function ThreatArc({ start, end, color, speed = 0.5, pulsing = false }) {
  const ref = useRef();
  const prog = useRef(0);
  const [geo] = useState(() => {
    const s = latLngToVec3(start[0], start[1]);
    const e = latLngToVec3(end[0], end[1]);
    const mid = s.clone().add(e).normalize().multiplyScalar(2.7);
    return new THREE.BufferGeometry().setFromPoints(
      new THREE.QuadraticBezierCurve3(s, mid, e).getPoints(60)
    );
  });
  useFrame((_, dt) => {
    prog.current = (prog.current + dt * speed) % 1;
    if (ref.current) ref.current.material.dashOffset = -prog.current * 10;
  });
  return (
    <line ref={ref} geometry={geo}>
      <lineDashedMaterial color={color} dashSize={0.08} gapSize={0.05}
        opacity={pulsing ? 0.95 : 0.75} transparent />
    </line>
  );
}

function Globe({ corridors, activeId }) {
  const ref = useRef();
  const nightMap = useLoader(THREE.TextureLoader, "/earth-night.jpg");
  
  useFrame((_, dt) => { 
    if (ref.current) ref.current.rotation.y += dt * 0.04; 
  });

  return (
    <group>
      <mesh ref={ref}>
        <sphereGeometry args={[2.0, 64, 64]} />
        <meshStandardMaterial 
          map={nightMap}
          emissiveMap={nightMap}
          emissiveIntensity={2.0}
          emissive="#ffffff"
          roughness={0.7}
          metalness={0.3}
        />
        
        {/* Enlight India - Strategic Glow */}
        <pointLight position={latLngToVec3(22, 77, 2.1)} intensity={6} color="#4488ff" distance={1.5} />
        <mesh position={latLngToVec3(22, 77, 2.01)}>
          <sphereGeometry args={[0.4, 32, 32]} />
          <meshBasicMaterial color="#4488ff" transparent opacity={0.15} />
        </mesh>

        {corridors.map(c => (
          <ThreatArc key={c.id} start={c.cities[0]} end={c.cities[1]}
            color={c.color || "#4488ff"} speed={(c.risk || 0.2) * 2 + 0.4}
            pulsing={activeId === c.id} />
        ))}
      </mesh>
      
      {/* Atmosphere / Halo */}
      <mesh>
        <sphereGeometry args={[2.1, 64, 64]} />
        <meshBasicMaterial color="#4488ff" transparent opacity={0.03} side={THREE.BackSide} />
      </mesh>

      <mesh rotation={[0, 0, Math.PI / 2]}>
        <torusGeometry args={[2.01, 0.002, 4, 80]} />
        <meshStandardMaterial color="#4488ff" opacity={0.12} transparent />
      </mesh>
    </group>
  );
}

// ── Radar chart SVG ───────────────────────────────────────────────
function RadarChart({ attribution, size = 200 }) {
  if (!attribution?.pct) return null;
  const keys = Object.keys(attribution.pct);
  const center = size / 2;
  const radius = size * 0.38;
  const n = keys.length;
  const angles = keys.map((_, i) => (i / n) * 2 * Math.PI - Math.PI / 2);

  const getPoint = (angle, r) => [
    center + r * Math.cos(angle),
    center + r * Math.sin(angle),
  ];

  // Outer ring points
  const outerPts = angles.map(a => getPoint(a, radius));
  // Value points
  const valPts = keys.map((k, i) => getPoint(angles[i], (attribution.pct[k] / 100) * radius));

  const poly = (pts) => pts.map(p => p.join(",")).join(" ");

  return (
    <svg width={size} height={size} style={{ overflow: "visible" }}>
      {/* Grid rings */}
      {[0.25, 0.5, 0.75, 1].map(f => (
        <polygon key={f}
          points={poly(angles.map(a => getPoint(a, radius * f)))}
          fill="none" stroke="#1a2040" strokeWidth={1} />
      ))}
      {/* Axes */}
      {angles.map((a, i) => (
        <line key={i} x1={center} y1={center}
          x2={outerPts[i][0]} y2={outerPts[i][1]}
          stroke="#1a2040" strokeWidth={1} />
      ))}
      {/* Data fill */}
      <polygon points={poly(valPts)} fill="#4488ff22" stroke="#4488ff" strokeWidth={2} />
      {/* Data dots */}
      {valPts.map((p, i) => (
        <circle key={i} cx={p[0]} cy={p[1]} r={4}
          fill={COMPONENT_COLORS[keys[i]] || "#4488ff"}
          stroke="#040810" strokeWidth={1.5} />
      ))}
      {/* Labels */}
      {keys.map((k, i) => {
        const [x, y] = getPoint(angles[i], radius + 22);
        const pct = attribution.pct[k];
        return (
          <g key={k}>
            <text x={x} y={y} textAnchor="middle" dominantBaseline="central"
              fontSize={9} fill="#6677aa">{COMPONENT_ICONS[k]} {k.replace(/_/g, " ")}</text>
            <text x={x} y={y + 12} textAnchor="middle" dominantBaseline="central"
              fontSize={10} fontWeight="700"
              fill={COMPONENT_COLORS[k] || "#4488ff"}>{pct}%</text>
          </g>
        );
      })}
    </svg>
  );
}

// ── Mini bar ──────────────────────────────────────────────────────
function RiskBar({ value, color, label, animate = true }) {
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
        <span style={{ fontSize: 11, color: "#6677aa" }}>{label}</span>
        <span style={{ fontSize: 11, fontWeight: 700, color }}>{(value * 100).toFixed(0)}%</span>
      </div>
      <div style={{ height: 4, background: "#1a2040", borderRadius: 2, overflow: "hidden" }}>
        <motion.div initial={{ width: 0 }} animate={{ width: `${value * 100}%` }}
          transition={{ duration: 1, ease: "easeOut" }}
          style={{ height: "100%", background: color, borderRadius: 2 }} />
      </div>
    </div>
  );
}

const inputStyle = {
  width: "100%", padding: "11px 14px",
  background: "#0a0e1a", border: "1px solid #1a2040",
  borderRadius: 8, color: "#e0e6f0",
  fontSize: 13, fontFamily: "'IBM Plex Mono',monospace", outline: "none",
};

// ═════════════════════════════════════════════════════════════════
export default function App() {
  // Auth
  const [token, setToken] = useState(localStorage.getItem("sc_token"));
  const [currentUser, setCurrentUser] = useState(JSON.parse(localStorage.getItem("sc_user") || "null"));
  const [authMode, setAuthMode] = useState("login");
  const [authError, setAuthError] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [step, setStep] = useState(0);
  const [regData, setRegData] = useState({
    name: "", email: "", password: "", business_name: "", business_type: "",
    location: "", language: "english", alert_channel: "whatsapp", phone: "",
    suppliers: [], highways: [],
  });

  // Globe state
  const [corridors, setCorridors] = useState(CORRIDORS_BASE.map(c => ({ ...c, risk: 0.15, color: "#4488ff" })));
  const [alerts, setAlerts] = useState([]);
  const [users, setUsers] = useState([]);
  const [sentimentSigs, setSentimentSigs] = useState([]);
  const [agriforecast, setAgriForecast] = useState(null);
  const [summary, setSummary] = useState(null);
  const [attributions, setAttributions] = useState({});
  const [peakAnalysis, setPeakAnalysis] = useState(null);
  const [activeTab, setActiveTab] = useState("map");
  const [activeCorr, setActiveCorr] = useState(null);
  const [systemOnline, setSystemOnline] = useState(false);
  const [cycleRunning, setCycleRunning] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);

  // User dashboard specific
  const [myDashboard, setMyDashboard] = useState(null);
  const [savings, setSavings] = useState(null);
  const [reasoning, setReasoning] = useState(null);
  const [reasoningLoading, setReasoningLoading] = useState(false);
  const [evolution, setEvolution] = useState(null);
  const [showRadar, setShowRadar] = useState(null); // highway id
  const [activeAttr, setActiveAttr] = useState(null);

  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {};

  // ── Fetch public data ────────────────────────────────────────────
  const fetchPublicData = useCallback(async () => {
    try {
      const [alertsR, usersR, summaryR, sentR, agriR, attrsR, peakR] = await Promise.all([
        axios.get(`${API}/alerts`),
        axios.get(`${API}/users`),
        axios.get(`${API}/intelligence-summary`),
        axios.get(`${API}/sentiment`),
        axios.get(`${API}/forecast/agri`),
        axios.get(`${API}/attributions`),
        axios.get(`${API}/peak-analysis`),
      ]);
      setAlerts(alertsR.data.alerts || []);
      setUsers(usersR.data.users || []);
      setSummary(summaryR.data);
      setSentimentSigs(sentR.data.signals || []);
      if (agriR.data.success) setAgriForecast(agriR.data);
      setAttributions(attrsR.data.attributions || {});
      setPeakAnalysis(peakR.data);
      setSystemOnline(true);
      setLastUpdated(new Date().toLocaleTimeString("en-IN"));
      const cr = summaryR.data.corridor_risks || {};
      setCorridors(CORRIDORS_BASE.map(c => {
        const r = cr[c.id]?.risk_score ?? 0.15;
        return { ...c, risk: r, color: riskColor(r) };
      }));
    } catch { setSystemOnline(false); }
  }, []);

  const fetchMyDashboard = useCallback(async () => {
    if (!token) return;
    try {
      const [dashR, savR] = await Promise.all([
        axios.get(`${API}/my-dashboard`, { headers: authHeaders }),
        axios.get(`${API}/savings/${currentUser?.id}`, { headers: authHeaders }).catch(() => ({ data: null })),
      ]);
      setMyDashboard(dashR.data);
      if (savR.data?.success) setSavings(savR.data);
    } catch { }
  }, [token, currentUser]);

  const fetchEvolution = useCallback(async () => {
    if (!token || !currentUser) return;
    try {
      const r = await axios.get(`${API}/intelligence-evolution/${currentUser.id}`, { headers: authHeaders });
      setEvolution(r.data);
    } catch { }
  }, [token, currentUser]);

  useEffect(() => {
    fetchPublicData();
    const iv = setInterval(fetchPublicData, 25000);
    return () => clearInterval(iv);
  }, [fetchPublicData]);

  useEffect(() => {
    if (token && currentUser) {
      fetchMyDashboard();
      fetchEvolution();
      const iv = setInterval(() => { fetchMyDashboard(); fetchEvolution(); }, 35000);
      return () => clearInterval(iv);
    }
  }, [token, fetchMyDashboard, fetchEvolution]);

  // Fetch Gemini reasoning for a corridor
  const fetchReasoning = async (hwId) => {
    setReasoningLoading(true);
    setReasoning(null);
    try {
      const r = await axios.get(`${API}/gemini-reasoning/${hwId}`);
      setReasoning(r.data);
    } catch { }
    setReasoningLoading(false);
  };

  // Fetch per-corridor attribution
  const fetchAttribution = async (hwId) => {
    setActiveAttr(null);
    try {
      const r = await axios.get(`${API}/attribution/${hwId}`);
      if (r.data.success) setActiveAttr(r.data);
    } catch { }
  };

  // ── Auth ─────────────────────────────────────────────────────────
  const handleLogin = async (e) => {
    e.preventDefault(); setAuthLoading(true); setAuthError("");
    try {
      const res = await axios.post(`${API}/login`, {
        email: e.target.email.value, password: e.target.password.value
      });
      localStorage.setItem("sc_token", res.data.access_token);
      localStorage.setItem("sc_user", JSON.stringify(res.data.user));
      setToken(res.data.access_token); setCurrentUser(res.data.user);
    } catch (err) { setAuthError(err.response?.data?.detail || "Login failed"); }
    setAuthLoading(false);
  };

  const handleRegister = async () => {
    setAuthLoading(true); setAuthError("");
    try {
      const payload = { ...regData, highways: regData.highways.length ? regData.highways : ["NH48"] };
      const res = await axios.post(`${API}/register`, payload);
      localStorage.setItem("sc_token", res.data.access_token);
      localStorage.setItem("sc_user", JSON.stringify(res.data.user));
      setToken(res.data.access_token); setCurrentUser(res.data.user);
    } catch (err) { setAuthError(err.response?.data?.detail || "Registration failed"); }
    setAuthLoading(false);
  };

  const handleLogout = () => {
    localStorage.removeItem("sc_token"); localStorage.removeItem("sc_user");
    setToken(null); setCurrentUser(null); setMyDashboard(null);
    setSavings(null); setEvolution(null);
  };

  const runCycle = async () => {
    setCycleRunning(true);
    try {
      await axios.post(`${API}/run-cycle`);
      await fetchPublicData();
      if (token) await fetchMyDashboard();
    } catch { }
    setCycleRunning(false);
  };

  const submitFeedback = async (alertId, action, highway = "", threatType = "") => {
    if (!token) return;
    try {
      await axios.post(`${API}/feedback/${alertId}`,
        { action, highway, threat_type: threatType, archetype: currentUser?.business_type || "" },
        { headers: authHeaders }
      );
      fetchMyDashboard();
    } catch { }
  };

  const fonts = `
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=IBM+Plex+Mono:wght@400;600&family=Noto+Sans+Devanagari&display=swap');
    *{box-sizing:border-box;margin:0;padding:0;}body{background:#040810;}
    input{outline:none;}input::placeholder{color:#334466;}
    ::-webkit-scrollbar{width:4px;}::-webkit-scrollbar-thumb{background:#1a2040;border-radius:2px;}
    @keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}
    @keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
    @keyframes shimmer{0%{background-position:-200px 0}100%{background-position:200px 0}}
  `;

  // ══════════════════════════════════════════════════════════════
  // AUTH SCREEN
  // ══════════════════════════════════════════════════════════════
  if (!token || !currentUser) {
    return (
      <div style={{
        display: "flex", minHeight: "100vh", background: "#040810",
        fontFamily: "'IBM Plex Mono',monospace", color: "#e0e6f0"
      }}>
        <style>{fonts}</style>

        {/* Left panel — globe */}
        <div style={{ flex: 1, position: "relative", overflow: "hidden" }}>
          <Canvas camera={{ position: [-0.8, 0.6, 5.2], fov: 45 }}>
            <ambientLight intensity={0.4} />
            <pointLight position={[10, 10, 10]} intensity={2} color="#4488ff" />
            <pointLight position={[-10, -5, -10]} intensity={0.6} color="#ff4444" />
            <Stars radius={100} depth={50} count={4000} factor={4} fade speed={0.3} />
            <Suspense fallback={null}><Globe corridors={corridors} activeId={null} /></Suspense>
            <OrbitControls enableZoom={false} enablePan={false} autoRotate autoRotateSpeed={0.5} />
          </Canvas>

          <div style={{
            position: "absolute", inset: 0, pointerEvents: "none",
            background: "linear-gradient(to right,transparent 55%,#040810)",
            display: "flex", flexDirection: "column", justifyContent: "center", padding: "0 0 0 44px"
          }}>
            <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
              <div style={{ fontSize: 10, color: "#4488ff", letterSpacing: 6, marginBottom: 12 }}>
                AI SUPPLY CHAIN INTELLIGENCE · INDIA
              </div>
              <div style={{
                fontSize: 52, fontFamily: "Syne,sans-serif", fontWeight: 800,
                color: "#e0e6f0", lineHeight: 1.1, marginBottom: 16
              }}>
                SENTINEL<br />CHAIN
              </div>
              <div style={{ fontSize: 13, color: "#6677aa", maxWidth: 320, lineHeight: 1.8 }}>
                India's first AI watchman for SME supply chains.
                Predicts disruptions 48–72 hrs early.
                Alerts in your language. Learns your risk tolerance.
              </div>
            </motion.div>

            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1 }}
              style={{ display: "flex", gap: 8, marginTop: 28, flexWrap: "wrap", maxWidth: 380 }}>
              {corridors.map(c => (
                <div key={c.id} style={{
                  display: "flex", alignItems: "center", gap: 5,
                  padding: "4px 10px", borderRadius: 20,
                  background: `${c.color}18`, border: `1px solid ${c.color}44`,
                  fontSize: 10, color: c.color, letterSpacing: 1
                }}>
                  <div style={{
                    width: 5, height: 5, borderRadius: "50%", background: c.color,
                    boxShadow: `0 0 6px ${c.color}`
                  }} />
                  {c.id} · {(c.risk * 100).toFixed(0)}%
                </div>
              ))}
            </motion.div>

            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.4 }}
              style={{ display: "flex", gap: 28, marginTop: 24 }}>
              {[{ v: "63M+", l: "SMEs Unprotected" }, { v: "₹8L Cr", l: "Wasted Yearly" }, { v: "70%", l: "Zero Digital Tools" }].map(s => (
                <div key={s.l}>
                  <div style={{ fontSize: 22, fontWeight: 700, color: "#ff4444", fontFamily: "Syne,sans-serif" }}>{s.v}</div>
                  <div style={{ fontSize: 10, color: "#334466" }}>{s.l}</div>
                </div>
              ))}
            </motion.div>
          </div>
        </div>

        {/* Right panel — auth */}
        <motion.div initial={{ opacity: 0, x: 40 }} animate={{ opacity: 1, x: 0 }}
          style={{
            width: 440, background: "#06090f", borderLeft: "1px solid #0d1530",
            display: "flex", flexDirection: "column", justifyContent: "center",
            padding: "40px 36px", overflowY: "auto"
          }}>

          <div style={{ marginBottom: 32 }}>
            <div style={{ fontSize: 10, color: "#334466", letterSpacing: 4, marginBottom: 6 }}>
              {authMode === "login" ? "WELCOME BACK" : step === 0 ? "CREATE ACCOUNT" : `SETUP · STEP ${step + 1}/3`}
            </div>
            <div style={{ fontSize: 26, fontFamily: "Syne,sans-serif", fontWeight: 700 }}>
              {authMode === "login" ? "Sign In" : step === 0 ? "Register" : ["Your Business", "Location & Prefs"][step - 1]}
            </div>
          </div>

          <AnimatePresence mode="wait">

            {authMode === "login" && (
              <motion.form key="login"
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }}
                onSubmit={handleLogin}>
                {[{ n: "email", t: "email", p: "you@company.com" }, { n: "password", t: "password", p: "••••••••" }].map(f => (
                  <div key={f.n} style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 10, color: "#6677aa", letterSpacing: 2, marginBottom: 6 }}>{f.n.toUpperCase()}</div>
                    <input name={f.n} type={f.t} placeholder={f.p} style={inputStyle} />
                  </div>
                ))}
                {authError && <div style={{
                  color: "#ff4444", fontSize: 12, marginBottom: 12,
                  padding: "8px 12px", background: "#ff444411", borderRadius: 6
                }}>{authError}</div>}
                <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                  type="submit" disabled={authLoading}
                  style={{
                    width: "100%", padding: 13, background: "linear-gradient(135deg,#4488ff,#2255cc)",
                    border: "none", borderRadius: 8, color: "#fff", fontSize: 13, letterSpacing: 2,
                    cursor: "pointer", fontFamily: "'IBM Plex Mono',monospace", marginBottom: 16,
                    opacity: authLoading ? 0.6 : 1
                  }}>
                  {authLoading ? "SIGNING IN..." : "SIGN IN →"}
                </motion.button>
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 10, color: "#334466", letterSpacing: 2, marginBottom: 10 }}>DEMO ACCOUNTS</div>
                  {[
                    { email: "arjun@mehtagarments.com", label: "Arjun — Textile Mfg", color: "#ff9900", pwd: "demo123" },
                    { email: "meena@kulkarnimedical.com", label: "Meena — Pharma Dist", color: "#4488ff", pwd: "demo123" },
                    { email: "ravi@patilcooperative.com", label: "Ravi — Agri Cooperative", color: "#00cc44", pwd: "demo123" },
                    { email: "admin@sentinelchain.in", label: "Admin Globe View", color: "#ff4444", pwd: "admin2026" },
                  ].map(d => (
                    <motion.button key={d.email} type="button" whileHover={{ x: 4 }}
                      onClick={() => {
                        document.querySelector("input[name=email]").value = d.email;
                        document.querySelector("input[name=password]").value = d.pwd;
                      }}
                      style={{
                        display: "flex", alignItems: "center", gap: 8, width: "100%",
                        padding: "7px 10px", marginBottom: 5, background: "#ffffff05",
                        border: `1px solid ${d.color}33`, borderRadius: 6, color: d.color,
                        fontSize: 11, cursor: "pointer", textAlign: "left",
                        fontFamily: "'IBM Plex Mono',monospace"
                      }}>
                      <div style={{ width: 6, height: 6, borderRadius: "50%", background: d.color }} />
                      {d.label}
                    </motion.button>
                  ))}
                </div>
                <div style={{ textAlign: "center", fontSize: 12, color: "#334466" }}>
                  New business?{" "}
                  <span onClick={() => { setAuthMode("register"); setAuthError(""); setStep(0); }}
                    style={{ color: "#4488ff", cursor: "pointer" }}>Register here</span>
                </div>
              </motion.form>
            )}

            {authMode === "register" && step === 0 && (
              <motion.div key="r0" initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -30 }}>
                {[{ k: "name", p: "Full name", l: "NAME" }, { k: "email", p: "work@email.com", l: "EMAIL", t: "email" },
                { k: "password", p: "Min 6 chars", l: "PASSWORD", t: "password" }, { k: "phone", p: "+91-XXXXX-XXXXX", l: "PHONE" }].map(f => (
                  <div key={f.k} style={{ marginBottom: 14 }}>
                    <div style={{ fontSize: 10, color: "#6677aa", letterSpacing: 2, marginBottom: 5 }}>{f.l}</div>
                    <input type={f.t || "text"} placeholder={f.p} value={regData[f.k]}
                      onChange={e => setRegData(p => ({ ...p, [f.k]: e.target.value }))} style={inputStyle} />
                  </div>
                ))}
                <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                  onClick={() => setStep(1)} disabled={!regData.name || !regData.email || !regData.password}
                  style={{
                    width: "100%", padding: 12, background: "linear-gradient(135deg,#4488ff,#2255cc)",
                    border: "none", borderRadius: 8, color: "#fff", fontSize: 13, letterSpacing: 2,
                    cursor: "pointer", fontFamily: "'IBM Plex Mono',monospace",
                    opacity: (!regData.name || !regData.email || !regData.password) ? 0.4 : 1
                  }}>NEXT →</motion.button>
                <div style={{ textAlign: "center", marginTop: 12, fontSize: 12, color: "#334466" }}>
                  Have account?{" "}
                  <span onClick={() => { setAuthMode("login"); setAuthError(""); }}
                    style={{ color: "#4488ff", cursor: "pointer" }}>Sign in</span>
                </div>
              </motion.div>
            )}

            {authMode === "register" && step === 1 && (
              <motion.div key="r1" initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -30 }}>
                <div style={{ fontSize: 10, color: "#6677aa", letterSpacing: 2, marginBottom: 6 }}>BUSINESS NAME</div>
                <input placeholder="e.g. Mehta Garments Pvt Ltd" value={regData.business_name}
                  onChange={e => setRegData(p => ({ ...p, business_name: e.target.value }))}
                  style={{ ...inputStyle, marginBottom: 16 }} />
                <div style={{ fontSize: 10, color: "#6677aa", letterSpacing: 2, marginBottom: 10 }}>BUSINESS TYPE</div>
                {BUSINESS_TYPES.map(bt => (
                  <motion.div key={bt.value} whileHover={{ x: 4 }}
                    onClick={() => setRegData(p => ({ ...p, business_type: bt.value, highways: [bt.highway] }))}
                    style={{
                      display: "flex", alignItems: "center", gap: 12, padding: "10px 14px",
                      marginBottom: 6, borderRadius: 8, cursor: "pointer",
                      background: regData.business_type === bt.value ? "#4488ff22" : "#ffffff05",
                      border: `1px solid ${regData.business_type === bt.value ? "#4488ff" : "#1a2040"}`
                    }}>
                    <span style={{ fontSize: 20 }}>{bt.icon}</span>
                    <div>
                      <div style={{ fontSize: 12, color: "#e0e6f0", fontWeight: 600 }}>{bt.label}</div>
                      <div style={{ fontSize: 10, color: "#6677aa" }}>{bt.region} · {bt.highway}</div>
                    </div>
                    {regData.business_type === bt.value && <div style={{ marginLeft: "auto", color: "#4488ff" }}>✓</div>}
                  </motion.div>
                ))}
                <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
                  <button onClick={() => setStep(0)} style={{
                    flex: 1, padding: 11, background: "#ffffff08",
                    border: "1px solid #1a2040", borderRadius: 8, color: "#6677aa", cursor: "pointer",
                    fontFamily: "'IBM Plex Mono',monospace", fontSize: 12
                  }}>← BACK</button>
                  <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                    onClick={() => setStep(2)} disabled={!regData.business_type}
                    style={{
                      flex: 2, padding: 11, background: "linear-gradient(135deg,#4488ff,#2255cc)",
                      border: "none", borderRadius: 8, color: "#fff", fontSize: 12, letterSpacing: 2,
                      cursor: "pointer", fontFamily: "'IBM Plex Mono',monospace",
                      opacity: !regData.business_type ? 0.4 : 1
                    }}>NEXT →</motion.button>
                </div>
              </motion.div>
            )}

            {authMode === "register" && step === 2 && (
              <motion.div key="r2" initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -30 }}>
                <div style={{ fontSize: 10, color: "#6677aa", letterSpacing: 2, marginBottom: 6 }}>YOUR CITY</div>
                <input placeholder="e.g. Ludhiana, Punjab" value={regData.location}
                  onChange={e => setRegData(p => ({ ...p, location: e.target.value }))}
                  style={{ ...inputStyle, marginBottom: 16 }} />
                <div style={{ fontSize: 10, color: "#6677aa", letterSpacing: 2, marginBottom: 10 }}>ALERT LANGUAGE</div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 16 }}>
                  {LANGUAGES.map(l => (
                    <motion.div key={l.value} whileHover={{ scale: 1.03 }}
                      onClick={() => setRegData(p => ({ ...p, language: l.value }))}
                      style={{
                        padding: 10, borderRadius: 8, textAlign: "center", cursor: "pointer",
                        background: regData.language === l.value ? "#4488ff22" : "#ffffff05",
                        border: `1px solid ${regData.language === l.value ? "#4488ff" : "#1a2040"}`,
                        color: regData.language === l.value ? "#4488ff" : "#6677aa", fontSize: 15
                      }}>
                      {l.label}
                    </motion.div>
                  ))}
                </div>
                <div style={{ fontSize: 10, color: "#6677aa", letterSpacing: 2, marginBottom: 10 }}>ALERT CHANNEL</div>
                <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
                  {[{ v: "whatsapp", l: "💬 WhatsApp" }, { v: "sms", l: "📱 SMS" }, { v: "app", l: "🔔 App" }].map(c => (
                    <motion.div key={c.v} whileHover={{ scale: 1.03 }}
                      onClick={() => setRegData(p => ({ ...p, alert_channel: c.v }))}
                      style={{
                        flex: 1, padding: 10, borderRadius: 8, textAlign: "center", cursor: "pointer",
                        background: regData.alert_channel === c.v ? "#4488ff22" : "#ffffff05",
                        border: `1px solid ${regData.alert_channel === c.v ? "#4488ff" : "#1a2040"}`,
                        color: regData.alert_channel === c.v ? "#4488ff" : "#6677aa", fontSize: 12
                      }}>
                      {c.l}
                    </motion.div>
                  ))}
                </div>
                {authError && <div style={{
                  color: "#ff4444", fontSize: 12, marginBottom: 12,
                  padding: "8px 12px", background: "#ff444411", borderRadius: 6
                }}>{authError}</div>}
                <div style={{ display: "flex", gap: 8 }}>
                  <button onClick={() => setStep(1)} style={{
                    flex: 1, padding: 11, background: "#ffffff08",
                    border: "1px solid #1a2040", borderRadius: 8, color: "#6677aa", cursor: "pointer",
                    fontFamily: "'IBM Plex Mono',monospace", fontSize: 12
                  }}>← BACK</button>
                  <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
                    onClick={handleRegister} disabled={authLoading || !regData.location}
                    style={{
                      flex: 2, padding: 11, background: "linear-gradient(135deg,#00cc44,#008833)",
                      border: "none", borderRadius: 8, color: "#fff", fontSize: 12, letterSpacing: 2,
                      cursor: "pointer", fontFamily: "'IBM Plex Mono',monospace",
                      opacity: (authLoading || !regData.location) ? 0.4 : 1
                    }}>
                    {authLoading ? "CREATING..." : "🛡️ ACTIVATE GUARDIAN"}
                  </motion.button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>
    );
  }

  // ══════════════════════════════════════════════════════════════
  // USER PERSONAL DASHBOARD (non-admin)
  // ══════════════════════════════════════════════════════════════
  if (token && currentUser && currentUser.role !== "admin") {
    const sc = { HIGH: "#ff4444", MEDIUM: "#ff9900", LOW: "#00cc44" };
    const dash = myDashboard;
    const totalSaved = savings?.total_saved_inr || 0;

    return (
      <div style={{
        minHeight: "100vh", background: "#040810",
        fontFamily: "'IBM Plex Mono',monospace", color: "#e0e6f0"
      }}>
        <style>{fonts}</style>

        {/* Nav */}
        <div style={{
          padding: "14px 32px", borderBottom: "1px solid #0d1530",
          display: "flex", alignItems: "center", justifyContent: "space-between",
          background: "#06090f", position: "sticky", top: 0, zIndex: 100
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ fontSize: 22, color: "#4488ff" }}>⬡</span>
            <div>
              <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: 4, fontFamily: "Syne,sans-serif" }}>SENTINELCHAIN</div>
              <div style={{ fontSize: 9, color: "#334466", letterSpacing: 2 }}>YOUR GUARDIAN IS WATCHING</div>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: 12 }}>{currentUser.name}</div>
              <div style={{ fontSize: 10, color: "#6677aa" }}>{currentUser.business_name}</div>
            </div>
            <div style={{
              width: 36, height: 36, borderRadius: "50%", background: "#4488ff33", color: "#4488ff",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 16, fontWeight: 700, fontFamily: "Syne,sans-serif"
            }}>
              {currentUser.name?.charAt(0)}
            </div>
            <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} onClick={handleLogout}
              style={{
                padding: "6px 14px", background: "#ff444411", border: "1px solid #ff444433",
                borderRadius: 6, color: "#ff4444", fontSize: 11, cursor: "pointer",
                fontFamily: "'IBM Plex Mono',monospace"
              }}>SIGN OUT</motion.button>
          </div>
        </div>

        <div style={{ padding: "24px 32px", maxWidth: 1300, margin: "0 auto" }}>

          {/* ── FEATURE 3: Cost of Silence Savings Counter ── */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            style={{
              padding: "20px 28px", borderRadius: 16, marginBottom: 20,
              background: "linear-gradient(135deg,#0d1225,#060918)",
              border: "1px solid #1a2040",
              display: "flex", alignItems: "center", justifyContent: "space-between",
              position: "relative", overflow: "hidden"
            }}>
            <div style={{
              position: "absolute", right: -40, top: -40, width: 200, height: 200,
              borderRadius: "50%", background: "radial-gradient(circle,#4488ff11,transparent)"
            }} />
            <div>
              <div style={{ fontSize: 10, color: "#4488ff", letterSpacing: 3, marginBottom: 6 }}>SUPPLY CHAIN STATUS</div>
              <div style={{ fontSize: 24, fontFamily: "Syne,sans-serif", fontWeight: 700, marginBottom: 4 }}>
                Namaste, {currentUser.name?.split(" ")[0]} 🙏
              </div>
              <div style={{ fontSize: 12, color: "#6677aa" }}>
                {currentUser.business_name} · {currentUser.location}
              </div>
            </div>
            <div style={{ display: "flex", gap: 24 }}>
              {/* Savings counter */}
              <div style={{
                textAlign: "center", padding: "12px 20px",
                background: "#00cc4411", border: "1px solid #00cc4433",
                borderRadius: 12
              }}>
                <div style={{ fontSize: 10, color: "#334466", letterSpacing: 2, marginBottom: 4 }}>
                  💰 WEALTH PROTECTED
                </div>
                <motion.div
                  key={totalSaved}
                  initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
                  style={{ fontSize: 28, fontWeight: 700, color: "#00cc44", fontFamily: "Syne,sans-serif" }}>
                  ₹{totalSaved.toLocaleString("en-IN")}
                </motion.div>
                <div style={{ fontSize: 10, color: "#334466" }}>saved via SentinelChain</div>
              </div>
              {[
                { label: "My Corridors", value: currentUser.highways?.length || 0, color: "#4488ff" },
                {
                  label: "Active Alerts", value: dash?.my_alerts?.length || 0,
                  color: dash?.my_alerts?.length > 0 ? "#ff4444" : "#00cc44"
                },
                { label: "Trust Score", value: `${((dash?.trust_score || 1) * 100).toFixed(0)}%`, color: "#00cc44" },
              ].map(s => (
                <div key={s.label} style={{ textAlign: "center" }}>
                  <div style={{ fontSize: 28, fontWeight: 700, color: s.color, fontFamily: "Syne,sans-serif" }}>{s.value}</div>
                  <div style={{ fontSize: 10, color: "#334466" }}>{s.label}</div>
                </div>
              ))}
            </div>
          </motion.div>

          {/* ── Grid row 1: Alerts + Corridors ── */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 20 }}>

            {/* My Alerts */}
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
              style={{ background: "#0d1225", border: "1px solid #1a2040", borderRadius: 14, padding: 24 }}>
              <div style={{ fontSize: 10, color: "#334466", letterSpacing: 3, marginBottom: 16 }}>🚨 MY ALERTS</div>
              {!dash?.my_alerts?.length ? (
                <div style={{
                  textAlign: "center", padding: "32px 16px", color: "#00cc44",
                  background: "#00cc4408", borderRadius: 10, border: "1px solid #00cc4422"
                }}>
                  <div style={{ fontSize: 28, marginBottom: 8 }}>✅</div>
                  <div style={{ fontSize: 13 }}>All clear for your corridors</div>
                  <div style={{ fontSize: 10, color: "#334466", marginTop: 4 }}>Guardian monitoring 24/7</div>
                </div>
              ) : dash.my_alerts.map((alert, i) => (
                <motion.div key={alert.alert_id}
                  initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.08 }}
                  style={{
                    padding: "14px 16px", marginBottom: 10, borderRadius: 10, background: "#0a0e1a",
                    borderLeft: `3px solid ${sc[alert.severity] || "#4488ff"}`,
                    border: `1px solid ${sc[alert.severity] || "#4488ff"}22`
                  }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                    <span style={{ fontSize: 11, color: "#6677aa" }}>🛣️ {alert.highway}</span>
                    <span style={{
                      fontSize: 10, padding: "2px 8px", borderRadius: 20, fontWeight: 700,
                      background: `${sc[alert.severity]}22`, color: sc[alert.severity]
                    }}>{alert.severity}</span>
                  </div>
                  <div style={{
                    fontSize: 13, color: "#4488ff", lineHeight: 1.7,
                    padding: "8px 10px", background: "#4488ff0a", borderRadius: 6, marginBottom: 8,
                    fontFamily: "Noto Sans Devanagari,sans-serif"
                  }}>
                    {alert.alert_text}
                  </div>
                  {alert.alert_text_english && (
                    <div style={{
                      fontSize: 11, color: "#aabbcc", fontStyle: "italic",
                      marginBottom: 8, lineHeight: 1.6
                    }}>"{alert.alert_text_english}"</div>
                  )}
                  <div style={{ fontSize: 11, color: "#ff9900", marginBottom: 10 }}>
                    💰 ₹{alert.counterfactual_cost_inr?.toLocaleString("en-IN")} at risk if ignored
                  </div>
                  <div style={{ display: "flex", gap: 6 }}>
                    {["acted", "ignored", "already_knew"].map(a => (
                      <motion.button key={a} whileHover={{ scale: 1.05 }}
                        onClick={() => submitFeedback(alert.alert_id, a, alert.highway)}
                        style={{
                          flex: 1, padding: "5px 4px", background: "#ffffff08",
                          border: "1px solid #1a2040", borderRadius: 4, color: "#6677aa",
                          cursor: "pointer", fontSize: 10, fontFamily: "'IBM Plex Mono',monospace"
                        }}>
                        {a === "acted" ? "✅ Acted" : a === "ignored" ? "❌ Ignored" : "💡 Knew"}
                      </motion.button>
                    ))}
                  </div>
                </motion.div>
              ))}
            </motion.div>

            {/* ── FEATURE 1: Risk Attribution per corridor ── */}
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}
              style={{ background: "#0d1225", border: "1px solid #1a2040", borderRadius: 14, padding: 24 }}>
              <div style={{ fontSize: 10, color: "#334466", letterSpacing: 3, marginBottom: 16 }}>
                🛣️ MY CORRIDORS — WHY IS IT RISKY?
              </div>
              {currentUser.highways?.map(hw => {
                const risk = dash?.corridor_risks?.[hw]?.risk_score || 0;
                const rc = riskColor(risk);
                const corr = CORRIDORS_BASE.find(c => c.id === hw);
                const attr = attributions[hw];
                const isExpanded = showRadar === hw;
                return (
                  <div key={hw} style={{
                    padding: 16, marginBottom: 10, borderRadius: 10,
                    background: "#0a0e1a", border: `1px solid ${rc}33`
                  }}>
                    <div style={{
                      display: "flex", justifyContent: "space-between", marginBottom: 10,
                      cursor: "pointer"
                    }} onClick={() => {
                      setShowRadar(isExpanded ? null : hw);
                      if (!isExpanded) { fetchAttribution(hw); fetchReasoning(hw); }
                    }}>
                      <div>
                        <div style={{ fontSize: 16, fontWeight: 700, color: rc, fontFamily: "Syne,sans-serif" }}>{hw}</div>
                        <div style={{ fontSize: 10, color: "#6677aa" }}>{corr?.name}</div>
                      </div>
                      <div style={{ textAlign: "right" }}>
                        <div style={{ fontSize: 22, fontWeight: 700, color: rc, fontFamily: "Syne,sans-serif" }}>
                          {(risk * 100).toFixed(0)}%
                        </div>
                        <div style={{ fontSize: 9, color: "#4488ff" }}>
                          {isExpanded ? "▲ hide breakdown" : "▼ why?"}
                        </div>
                      </div>
                    </div>
                    <div style={{ height: 6, background: "#1a2040", borderRadius: 3, marginBottom: 8, overflow: "hidden" }}>
                      <motion.div initial={{ width: 0 }} animate={{ width: `${risk * 100}%` }}
                        transition={{ duration: 1, ease: "easeOut" }}
                        style={{ height: "100%", background: rc, borderRadius: 3 }} />
                    </div>

                    {/* FEATURE 4: Signal propagation attribution bars */}
                    {attr && (
                      <AnimatePresence>
                        {isExpanded && (
                          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.3 }}>
                            <div style={{ marginTop: 12, marginBottom: 12 }}>
                              <div style={{ fontSize: 10, color: "#334466", letterSpacing: 2, marginBottom: 10 }}>
                                RISK ATTRIBUTION — SIGNAL BREAKDOWN
                              </div>
                              {Object.entries(attr.components || {}).map(([k, v]) => (
                                <RiskBar key={k} value={v}
                                  color={COMPONENT_COLORS[k] || "#4488ff"}
                                  label={`${COMPONENT_ICONS[k] || ""} ${(attr.labels || {})[k] || k} (${attr.pct?.[k] || 0}%)`} />
                              ))}
                              <div style={{ fontSize: 10, color: "#334466", marginTop: 8 }}>
                                Primary driver:{" "}
                                <span style={{ color: COMPONENT_COLORS[attr.top_driver] || "#4488ff", fontWeight: 700 }}>
                                  {(attr.labels || {})[attr.top_driver] || attr.top_driver}
                                </span>
                              </div>
                            </div>

                            {/* Radar chart */}
                            <div style={{ display: "flex", justifyContent: "center", marginBottom: 12 }}>
                              <RadarChart attribution={activeAttr || attr} size={200} />
                            </div>

                            {/* FEATURE 2: Gemini reasoning chain */}
                            {reasoningLoading ? (
                              <div style={{ fontSize: 11, color: "#334466", textAlign: "center", padding: 12 }}>
                                🧠 Gemini analyzing reasoning chain...
                              </div>
                            ) : reasoning?.reasoning && (
                              <div style={{
                                background: "#0a0e1a", borderRadius: 8, padding: 14,
                                border: "1px solid #4488ff22"
                              }}>
                                <div style={{ fontSize: 10, color: "#334466", letterSpacing: 2, marginBottom: 10 }}>
                                  🤖 GEMINI STRATEGIC ADVISOR
                                </div>
                                <div style={{ marginBottom: 10 }}>
                                  <div style={{ fontSize: 10, color: "#6677aa", marginBottom: 6 }}>LOGIC CHAIN</div>
                                  {reasoning.reasoning.reasoning_chain?.map((step, i) => (
                                    <div key={i} style={{
                                      display: "flex", gap: 8, marginBottom: 5,
                                      alignItems: "flex-start"
                                    }}>
                                      <div style={{
                                        width: 18, height: 18, borderRadius: "50%",
                                        background: "#4488ff22", color: "#4488ff",
                                        display: "flex", alignItems: "center", justifyContent: "center",
                                        fontSize: 9, fontWeight: 700, flexShrink: 0
                                      }}>{i + 1}</div>
                                      <div style={{ fontSize: 11, color: "#aabbcc", lineHeight: 1.5 }}>{step}</div>
                                    </div>
                                  ))}
                                </div>
                                <div style={{
                                  padding: "8px 10px", background: "#ff444411",
                                  borderRadius: 6, marginBottom: 8
                                }}>
                                  <div style={{ fontSize: 9, color: "#334466", marginBottom: 4 }}>
                                    COUNTERFACTUAL — IF YOU IGNORE THIS
                                  </div>
                                  <div style={{ fontSize: 11, color: "#ff4444", lineHeight: 1.5 }}>
                                    {reasoning.reasoning.counterfactual_outcome}
                                  </div>
                                </div>
                                <div style={{ padding: "8px 10px", background: "#00cc4411", borderRadius: 6 }}>
                                  <div style={{ fontSize: 9, color: "#334466", marginBottom: 4 }}>→ ACTION NOW</div>
                                  <div style={{ fontSize: 11, color: "#00cc44", lineHeight: 1.5 }}>
                                    {reasoning.reasoning.specific_action}
                                  </div>
                                </div>
                                {reasoning.reasoning.sources_used?.length > 0 && (
                                  <div style={{ marginTop: 8 }}>
                                    <div style={{ fontSize: 9, color: "#334466", marginBottom: 4 }}>
                                      SIGNALS USED BY GEMINI
                                    </div>
                                    {reasoning.reasoning.sources_used.slice(0, 2).map((s, i) => (
                                      <div key={i} style={{
                                        fontSize: 10, color: "#6677aa",
                                        marginBottom: 3, padding: "3px 6px",
                                        background: "#ffffff05", borderRadius: 4
                                      }}>
                                        📰 {s}
                                      </div>
                                    ))}
                                  </div>
                                )}
                                <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8 }}>
                                  <span style={{ fontSize: 10, color: "#6677aa" }}>
                                    Confidence:{" "}
                                    <span style={{
                                      color: reasoning.reasoning.confidence === "HIGH" ? "#00cc44" :
                                        reasoning.reasoning.confidence === "LOW" ? "#ff4444" : "#ff9900"
                                    }}>
                                      {reasoning.reasoning.confidence}
                                    </span>
                                  </span>
                                </div>
                              </div>
                            )}
                          </motion.div>
                        )}
                      </AnimatePresence>
                    )}
                  </div>
                );
              })}

              {/* Active Shipments */}
              {dash?.active_shipments?.length > 0 && (
                <>
                  <div style={{ fontSize: 10, color: "#334466", letterSpacing: 3, margin: "16px 0 10px" }}>
                    📦 ACTIVE SHIPMENTS
                  </div>
                  {dash.active_shipments.map(s => (
                    <div key={s.id} style={{
                      padding: "10px 12px", borderRadius: 8,
                      background: "#4488ff0a", border: "1px solid #4488ff22", marginBottom: 6
                    }}>
                      <div style={{ fontSize: 12, color: "#4488ff" }}>{s.from} → {s.to}</div>
                      <div style={{ fontSize: 10, color: "#6677aa", marginTop: 2 }}>
                        via {s.via} · ₹{s.value_inr?.toLocaleString("en-IN")} · arrives {s.expected_arrival}
                      </div>
                    </div>
                  ))}
                </>
              )}
            </motion.div>
          </div>

          {/* ── Grid row 2: Forecast + Intelligence Evolution ── */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 20 }}>

            {/* Commodity forecast */}
            {dash?.commodity_forecast && (
              <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}
                style={{ background: "#0d1225", border: "1px solid #1a2040", borderRadius: 14, padding: 24 }}>
                <div style={{ fontSize: 10, color: "#334466", letterSpacing: 3, marginBottom: 16 }}>
                  📈 7-DAY PRICE FORECAST — {dash.commodity_forecast.commodity?.toUpperCase()}
                </div>
                <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
                  <div style={{
                    padding: "12px 16px", background: "#00cc4411",
                    border: "1px solid #00cc4433", borderRadius: 10, textAlign: "center", flex: 1
                  }}>
                    <div style={{ fontSize: 10, color: "#334466", marginBottom: 4 }}>CURRENT</div>
                    <div style={{ fontSize: 22, fontWeight: 700, color: "#00cc44", fontFamily: "Syne,sans-serif" }}>
                      ₹{dash.commodity_forecast.current_price?.toLocaleString("en-IN")}
                    </div>
                    <div style={{ fontSize: 9, color: "#6677aa" }}>{dash.commodity_forecast.unit}</div>
                  </div>
                  {dash.commodity_forecast.spike_alert ? (
                    <div style={{
                      padding: "12px 16px", background: "#ff444411",
                      border: "1px solid #ff444444", borderRadius: 10, textAlign: "center", flex: 1
                    }}>
                      <div style={{ fontSize: 10, color: "#ff4444", marginBottom: 4 }}>
                        ⚠️ {dash.commodity_forecast.spike_alert.type}
                      </div>
                      <div style={{ fontSize: 22, fontWeight: 700, color: "#ff4444", fontFamily: "Syne,sans-serif" }}>
                        {dash.commodity_forecast.spike_alert.change_pct > 0 ? "+" : ""}
                        {dash.commodity_forecast.spike_alert.change_pct?.toFixed(1)}%
                      </div>
                    </div>
                  ) : (
                    <div style={{
                      padding: "12px 16px", background: "#00cc4408",
                      border: "1px solid #00cc4422", borderRadius: 10, textAlign: "center", flex: 1
                    }}>
                      <div style={{ fontSize: 14, fontWeight: 700, color: "#00cc44" }}>STABLE</div>
                      <div style={{ fontSize: 9, color: "#6677aa" }}>No spike detected</div>
                    </div>
                  )}
                </div>
                {/* Animated bar chart */}
                <div style={{ display: "flex", gap: 3, alignItems: "flex-end", height: 68 }}>
                  {dash.commodity_forecast.forecasts?.slice(0, 7).map((f, i) => {
                    const prices = dash.commodity_forecast.forecasts.map(x => x.predicted_price);
                    const mn = Math.min(...prices), mx = Math.max(...prices);
                    const h = ((f.predicted_price - mn) / (mx - mn + 1)) * 50 + 18;
                    return (
                      <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                        <motion.div initial={{ height: 0 }} animate={{ height: h }}
                          transition={{ delay: i * 0.05, duration: 0.6, ease: "easeOut" }}
                          style={{
                            width: "100%", borderRadius: "3px 3px 0 0", minHeight: 4,
                            background: f.predicted_price === mx ? "#ff4444" : "#4488ff"
                          }} />
                        <div style={{ fontSize: 8, color: "#334466" }}>
                          {new Date(f.date).getDate()}/{new Date(f.date).getMonth() + 1}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </motion.div>
            )}

            {/* ── FEATURE 5: Intelligence Evolution Widget ── */}
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}
              style={{ background: "#0d1225", border: "1px solid #1a2040", borderRadius: 14, padding: 24 }}>
              <div style={{ fontSize: 10, color: "#334466", letterSpacing: 3, marginBottom: 16 }}>
                🧠 INTELLIGENCE EVOLUTION
              </div>
              {evolution ? (
                <div>
                  {/* Learning stage */}
                  <div style={{
                    display: "flex", justifyContent: "space-between", alignItems: "center",
                    marginBottom: 16, padding: "10px 14px",
                    background: "#4488ff11", borderRadius: 8, border: "1px solid #4488ff22"
                  }}>
                    <div>
                      <div style={{ fontSize: 10, color: "#334466", marginBottom: 3 }}>LEARNING STAGE</div>
                      <div style={{
                        fontSize: 16, fontWeight: 700, color: "#4488ff",
                        fontFamily: "Syne,sans-serif"
                      }}>{evolution.learning_stage}</div>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontSize: 10, color: "#334466", marginBottom: 3 }}>YOUR ACT RATE</div>
                      <div style={{
                        fontSize: 22, fontWeight: 700,
                        color: evolution.act_rate > 0.5 ? "#00cc44" : evolution.act_rate > 0.3 ? "#ff9900" : "#ff4444",
                        fontFamily: "Syne,sans-serif"
                      }}>
                        {((evolution.act_rate || 0) * 100).toFixed(0)}%
                      </div>
                    </div>
                  </div>

                  {/* Threshold calibration */}
                  <div style={{ marginBottom: 14 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                      <span style={{ fontSize: 11, color: "#6677aa" }}>Base threshold</span>
                      <span style={{ fontSize: 11, color: "#6677aa" }}>
                        {((evolution.base_threshold || 0.45) * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                      <span style={{ fontSize: 11, color: "#4488ff", fontWeight: 600 }}>Your calibrated threshold</span>
                      <span style={{ fontSize: 11, color: "#4488ff", fontWeight: 600 }}>
                        {((evolution.calibrated_threshold || 0.45) * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div style={{
                      height: 6, background: "#1a2040", borderRadius: 3, marginBottom: 4,
                      position: "relative", overflow: "hidden"
                    }}>
                      <motion.div animate={{ width: `${(evolution.base_threshold || 0.45) * 100}%` }}
                        style={{ height: "100%", background: "#334466", borderRadius: 3, position: "absolute" }} />
                      <motion.div animate={{ width: `${(evolution.calibrated_threshold || 0.45) * 100}%` }}
                        transition={{ duration: 1.5, ease: "easeOut" }}
                        style={{ height: "100%", background: "#4488ff", borderRadius: 3, position: "absolute" }} />
                    </div>
                    <div style={{ fontSize: 10, color: "#334466" }}>
                      {evolution.calibrated_threshold < evolution.base_threshold
                        ? "↓ More sensitive — system sees you act fast on risks"
                        : evolution.calibrated_threshold > evolution.base_threshold
                          ? "↑ Higher threshold — filtering low-confidence alerts for you"
                          : "→ System still calibrating your preferences"}
                    </div>
                  </div>

                  {/* System insights */}
                  <div>
                    <div style={{ fontSize: 10, color: "#334466", letterSpacing: 2, marginBottom: 10 }}>
                      WHAT THE SYSTEM HAS LEARNED
                    </div>
                    {evolution.system_insights?.length > 0 ? evolution.system_insights.map((ins, i) => (
                      <motion.div key={i}
                        initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.1 }}
                        style={{
                          display: "flex", gap: 8, alignItems: "flex-start", marginBottom: 8,
                          padding: "8px 10px", background: "#ffffff05", borderRadius: 6,
                          border: "1px solid #1a2040"
                        }}>
                        <span style={{ color: "#4488ff", fontSize: 14, flexShrink: 0 }}>⬡</span>
                        <div style={{ fontSize: 11, color: "#aabbcc", lineHeight: 1.6 }}>{ins}</div>
                      </motion.div>
                    )) : (
                      <div style={{
                        fontSize: 11, color: "#334466", textAlign: "center", padding: "16px",
                        background: "#ffffff03", borderRadius: 6
                      }}>
                        Keep using the feedback buttons to teach the system your preferences.
                        <div style={{ fontSize: 10, marginTop: 6, color: "#4488ff" }}>
                          Every ✅ Acted / ❌ Ignored click makes alerts smarter for your business.
                        </div>
                      </div>
                    )}
                  </div>

                  <div style={{
                    marginTop: 14, padding: "10px", background: "#ff990011",
                    borderRadius: 6, border: "1px solid #ff990033"
                  }}>
                    <div style={{ fontSize: 10, color: "#334466", marginBottom: 4 }}>
                      ARCHETYPE TRUST SCORE
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div style={{ fontSize: 11, color: "#6677aa" }}>
                        {currentUser.business_type?.replace(/_/g, " ")}
                      </div>
                      <div style={{
                        fontSize: 18, fontWeight: 700, color: "#ff9900",
                        fontFamily: "Syne,sans-serif"
                      }}>
                        {((evolution.archetype_trust_score || 0.5) * 100).toFixed(0)}%
                      </div>
                    </div>
                    <div style={{ height: 4, background: "#1a2040", borderRadius: 2, marginTop: 6, overflow: "hidden" }}>
                      <motion.div animate={{ width: `${(evolution.archetype_trust_score || 0.5) * 100}%` }}
                        transition={{ duration: 1.5 }}
                        style={{ height: "100%", background: "#ff9900", borderRadius: 2 }} />
                    </div>
                  </div>
                </div>
              ) : (
                <div style={{ fontSize: 11, color: "#334466", textAlign: "center", padding: 32 }}>
                  Loading intelligence data...
                </div>
              )}
            </motion.div>
          </div>

          {/* ── FEATURE: Peak Disruption Historical Insights ── */}
          {peakAnalysis && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}
              style={{ background: "#0d1225", border: "1px solid #1a2040", borderRadius: 14, padding: 24, marginBottom: 20 }}>
              <div style={{ fontSize: 10, color: "#334466", letterSpacing: 3, marginBottom: 16 }}>
                📊 HISTORICAL DISRUPTION RANKING — ALL CORRIDORS
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 12 }}>
                {peakAnalysis.ranked_corridors?.slice(0, 6).map((corr, i) => (
                  <div key={corr.highway} style={{
                    padding: "12px 14px", borderRadius: 10,
                    background: "#0a0e1a",
                    border: `1px solid ${riskColor(corr.current_risk)}33`
                  }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                      <div>
                        <div style={{
                          fontSize: 14, fontWeight: 700,
                          color: riskColor(corr.current_risk), fontFamily: "Syne,sans-serif"
                        }}>
                          {corr.highway}
                        </div>
                        <div style={{ fontSize: 9, color: "#334466" }}>#{i + 1} ranked</div>
                      </div>
                      <div style={{
                        fontSize: 18, fontWeight: 700,
                        color: riskColor(corr.current_risk), fontFamily: "Syne,sans-serif"
                      }}>
                        {(corr.current_risk * 100).toFixed(0)}%
                      </div>
                    </div>
                    <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                      {corr.weather_component > 0.05 && (
                        <span style={{
                          fontSize: 9, padding: "2px 6px", background: "#4488ff11",
                          borderRadius: 3, color: "#4488ff"
                        }}>🌧️ {(corr.weather_component * 100).toFixed(0)}%</span>
                      )}
                      {corr.sentiment_component > 0.05 && (
                        <span style={{
                          fontSize: 9, padding: "2px 6px", background: "#ff990011",
                          borderRadius: 3, color: "#ff9900"
                        }}>📰 {(corr.sentiment_component * 100).toFixed(0)}%</span>
                      )}
                      {corr.port_component > 0.05 && (
                        <span style={{
                          fontSize: 9, padding: "2px 6px", background: "#ff444411",
                          borderRadius: 3, color: "#ff4444"
                        }}>⚓ {(corr.port_component * 100).toFixed(0)}%</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              {peakAnalysis.most_volatile && (
                <div style={{
                  marginTop: 12, padding: "8px 12px", background: "#ff444411",
                  borderRadius: 6, border: "1px solid #ff444433", fontSize: 11, color: "#ff4444"
                }}>
                  ⚠️ Most volatile corridor: <strong>{peakAnalysis.most_volatile}</strong>
                  {" "}· Safest: <strong style={{ color: "#00cc44" }}>{peakAnalysis.safest}</strong>
                </div>
              )}
            </motion.div>
          )}

          <div style={{ textAlign: "center" }}>
            <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
              onClick={() => { fetchPublicData(); fetchMyDashboard(); fetchEvolution(); }}
              style={{
                padding: "12px 28px", background: "linear-gradient(135deg,#4488ff22,#4488ff11)",
                border: "1px solid #4488ff44", borderRadius: 8, color: "#4488ff", fontSize: 12,
                letterSpacing: 2, cursor: "pointer", fontFamily: "'IBM Plex Mono',monospace"
              }}>
              ↻ REFRESH INTELLIGENCE
            </motion.button>
          </div>
        </div>
      </div>
    );
  }

  // ══════════════════════════════════════════════════════════════
  // ADMIN GLOBE DASHBOARD
  // ══════════════════════════════════════════════════════════════
  const threatLevel = summary?.threat_level || "NORMAL";
  const tlColor = threatLevel === "CRITICAL" ? "#ff4444" : threatLevel === "ELEVATED" ? "#ff9900" : "#00cc44";

  return (
    <div style={{
      display: "flex", height: "100vh", background: "#040810",
      color: "#e0e6f0", overflow: "hidden", fontFamily: "'IBM Plex Mono',monospace"
    }}>
      <style>{fonts}</style>

      {/* Sidebar */}
      <div style={{
        width: 72, background: "#06090f", borderRight: "1px solid #0d1530",
        display: "flex", flexDirection: "column", alignItems: "center",
        padding: "20px 0", gap: 8, zIndex: 10
      }}>
        <div style={{ fontSize: 28, color: "#4488ff", marginBottom: 24 }}>⬡</div>
        {[
          { id: "map", icon: "🌐", label: "Map" },
          { id: "alerts", icon: "🚨", label: "Alerts" },
          { id: "corridors", icon: "🛣️", label: "Corridors" },
          { id: "users", icon: "👤", label: "Users" },
          { id: "intel", icon: "🧠", label: "Intel" },
        ].map(tab => (
          <motion.button key={tab.id} whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.95 }}
            onClick={() => setActiveTab(tab.id)} title={tab.label}
            style={{
              width: 44, height: 44, borderRadius: 10,
              background: activeTab === tab.id ? "#4488ff22" : "transparent",
              border: activeTab === tab.id ? "1px solid #4488ff44" : "1px solid transparent",
              color: activeTab === tab.id ? "#4488ff" : "#334466",
              fontSize: 18, cursor: "pointer",
              display: "flex", alignItems: "center", justifyContent: "center"
            }}>
            {tab.icon}
          </motion.button>
        ))}
        <div style={{ marginTop: "auto", display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
          <div style={{
            width: 8, height: 8, borderRadius: "50%",
            background: systemOnline ? "#00cc44" : "#ff4444",
            boxShadow: `0 0 10px ${systemOnline ? "#00cc44" : "#ff4444"}`
          }} />
          <div style={{ fontSize: 9, color: "#334466", writingMode: "vertical-rl" }}>
            {systemOnline ? "ONLINE" : "OFFLINE"}
          </div>
          <motion.button whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.95 }}
            onClick={handleLogout} title="Sign out"
            style={{
              width: 36, height: 36, borderRadius: 8, background: "#ff444411",
              border: "1px solid #ff444433", color: "#ff4444", fontSize: 14, cursor: "pointer",
              display: "flex", alignItems: "center", justifyContent: "center"
            }}>↩</motion.button>
        </div>
      </div>

      {/* Globe */}
      <div style={{ flex: 1, position: "relative" }}>
        <div style={{
          position: "absolute", inset: 0, zIndex: 1, pointerEvents: "none",
          background: "repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,0.025) 2px,rgba(0,0,0,0.025) 4px)"
        }} />

        <div style={{
          position: "absolute", top: 0, left: 0, right: 0, zIndex: 5, padding: "18px 28px",
          background: "linear-gradient(to bottom,#040810dd,transparent)",
          display: "flex", alignItems: "center", justifyContent: "space-between"
        }}>
          <div>
            <div style={{
              fontSize: 22, fontFamily: "Syne,sans-serif", fontWeight: 800,
              letterSpacing: 6, color: "#e0e6f0"
            }}>SENTINELCHAIN</div>
            <div style={{ fontSize: 10, color: "#4488ff", letterSpacing: 3 }}>
              SUPPLY CHAIN GUARDIAN · INDIA · ADMIN
            </div>
          </div>
          <div style={{ display: "flex", gap: 20, alignItems: "center" }}>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: 10, color: "#334466" }}>THREAT LEVEL</div>
              <div style={{
                fontSize: 20, fontWeight: 700, color: tlColor, fontFamily: "Syne,sans-serif",
                animation: threatLevel === "CRITICAL" ? "pulse 1s infinite" : "none"
              }}>{threatLevel}</div>
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: 10, color: "#334466" }}>MAX RISK</div>
              <div style={{
                fontSize: 20, fontWeight: 700,
                color: riskColor(summary?.max_corridor_risk || 0), fontFamily: "Syne,sans-serif"
              }}>
                {((summary?.max_corridor_risk || 0) * 100).toFixed(0)}%
              </div>
            </div>
            <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
              onClick={runCycle} disabled={cycleRunning}
              style={{
                padding: "8px 16px", background: "linear-gradient(135deg,#4488ff22,#4488ff11)",
                border: "1px solid #4488ff44", color: "#4488ff", borderRadius: 8, cursor: "pointer",
                fontSize: 11, letterSpacing: 2, fontFamily: "'IBM Plex Mono',monospace",
                opacity: cycleRunning ? 0.5 : 1
              }}>
              <span style={{ display: "inline-block", animation: cycleRunning ? "spin 1s linear infinite" : "none" }}>↻</span>
              {" "}RUN CYCLE
            </motion.button>
          </div>
        </div>

        <Canvas camera={{ position: [-0.8, 0.6, 5.2], fov: 45 }}
          style={{ background: "radial-gradient(ellipse at center,#040d1f 0%,#020408 100%)" }}>
          <ambientLight intensity={0.5} />
          <pointLight position={[10, 10, 10]} intensity={2} color="#4488ff" />
          <pointLight position={[-10, -10, -10]} intensity={0.8} color="#ff4444" />
          <Stars radius={100} depth={50} count={3000} factor={4} fade speed={0.5} />
          <Suspense fallback={null}><Globe corridors={corridors} activeId={activeCorr} /></Suspense>
          <OrbitControls enableZoom enablePan={false} minDistance={3.5} maxDistance={9}
            autoRotate={!activeCorr} autoRotateSpeed={0.4} target={[0.3, 0.1, 0]} />
        </Canvas>

        <div style={{
          position: "absolute", bottom: 0, left: 0, right: 0, zIndex: 5, padding: "18px 28px",
          background: "linear-gradient(to top,#040810dd,transparent)",
          display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center"
        }}>
          {corridors.map(c => (
            <motion.div key={c.id} whileHover={{ scale: 1.05 }}
              onClick={() => {
                const next = activeCorr === c.id ? null : c.id;
                setActiveCorr(next);
                if (next) { fetchAttribution(next); fetchReasoning(next); }
              }}
              style={{
                display: "flex", alignItems: "center", gap: 6, padding: "5px 12px", borderRadius: 20,
                background: activeCorr === c.id ? `${c.color}22` : "#ffffff08",
                border: `1px solid ${activeCorr === c.id ? c.color : "#1a2040"}`, cursor: "pointer"
              }}>
              <div style={{
                width: 6, height: 6, borderRadius: "50%", background: c.color,
                boxShadow: `0 0 6px ${c.color}`
              }} />
              <span style={{ fontSize: 10, color: c.color, letterSpacing: 1 }}>{c.id}</span>
              <span style={{ fontSize: 10, color: "#334466" }}>{(c.risk * 100).toFixed(0)}%</span>
            </motion.div>
          ))}
          <div style={{ marginLeft: "auto", fontSize: 10, color: "#334466" }}>Updated: {lastUpdated || "—"}</div>
        </div>
      </div>

      {/* Right panel */}
      <AnimatePresence mode="wait">
        <motion.div key={activeTab}
          initial={{ opacity: 0, x: 40 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 40 }}
          transition={{ type: "spring", stiffness: 120, damping: 20 }}
          style={{
            width: 380, background: "#06090f", borderLeft: "1px solid #0d1530",
            display: "flex", flexDirection: "column", overflow: "hidden", zIndex: 10
          }}>

          <div style={{ padding: "18px 20px 14px", borderBottom: "1px solid #0d1530", background: "#040810" }}>
            <div style={{ fontSize: 10, color: "#334466", letterSpacing: 3, marginBottom: 4 }}>
              {activeTab === "map" && "LIVE INTELLIGENCE"}
              {activeTab === "alerts" && "ACTIVE ALERTS"}
              {activeTab === "corridors" && "CORRIDOR STATUS"}
              {activeTab === "users" && "MONITORED BUSINESSES"}
              {activeTab === "intel" && "ML INSIGHTS + ATTRIBUTION"}
            </div>
            <div style={{ fontSize: 18, fontWeight: 700, fontFamily: "Syne,sans-serif" }}>
              {activeTab === "map" && "System Overview"}
              {activeTab === "alerts" && `${alerts.length} Alerts`}
              {activeTab === "corridors" && "Highway Network"}
              {activeTab === "users" && `${users.length} Businesses`}
              {activeTab === "intel" && "Intelligence Report"}
            </div>
          </div>

          <div style={{ flex: 1, overflowY: "auto", padding: 16 }}>

            {activeTab === "map" && (
              <div>
                {[
                  { label: "Signal Mesh Nodes", value: "32", color: "#4488ff" },
                  { label: "Corridors Monitored", value: "6", color: "#00cc44" },
                  { label: "Businesses Protected", value: users.length, color: "#ff9900" },
                  { label: "Data Sources Live", value: "4", color: "#4488ff" },
                ].map(s => (
                  <div key={s.label} style={{
                    display: "flex", justifyContent: "space-between",
                    padding: "11px 14px", marginBottom: 6, background: "#ffffff05",
                    borderRadius: 8, border: "1px solid #0d1530"
                  }}>
                    <span style={{ fontSize: 11, color: "#6677aa" }}>{s.label}</span>
                    <span style={{ fontSize: 14, fontWeight: 700, color: s.color, fontFamily: "Syne,sans-serif" }}>{s.value}</span>
                  </div>
                ))}

                <div style={{ margin: "16px 0 10px", fontSize: 10, color: "#334466", letterSpacing: 2 }}>
                  ACTIVE THREAT CORRIDORS
                </div>
                {corridors.filter(c => c.risk > 0.25).map(c => (
                  <motion.div key={c.id} whileHover={{ x: 4 }}
                    onClick={() => {
                      const next = activeCorr === c.id ? null : c.id;
                      setActiveCorr(next);
                      if (next) { fetchAttribution(next); fetchReasoning(next); }
                    }}
                    style={{
                      display: "flex", alignItems: "center", gap: 12, padding: "10px 14px",
                      borderRadius: 8, marginBottom: 6, cursor: "pointer",
                      background: activeCorr === c.id ? `${c.color}18` : "#ffffff05",
                      border: `1px solid ${activeCorr === c.id ? c.color + "66" : "#1a2040"}`
                    }}>
                    <div style={{ width: 8, height: 8, borderRadius: "50%", background: c.color, boxShadow: `0 0 8px ${c.color}` }} />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 12, color: "#e0e6f0", fontWeight: 600 }}>{c.id}</div>
                      <div style={{ fontSize: 10, color: "#6677aa" }}>{c.name}</div>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div style={{ fontSize: 13, fontWeight: 700, color: c.color }}>{(c.risk * 100).toFixed(0)}%</div>
                    </div>
                  </motion.div>
                ))}

                {/* Sentiment signals */}
                {sentimentSigs.length > 0 && (
                  <>
                    <div style={{ margin: "16px 0 10px", fontSize: 10, color: "#334466", letterSpacing: 2 }}>
                      GEMINI SENTIMENT SIGNALS
                    </div>
                    {sentimentSigs.slice(0, 3).map((sig, i) => (
                      <motion.div key={i}
                        initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.1 }}
                        style={{
                          padding: "10px 12px", marginBottom: 8, borderRadius: 8,
                          background: sig.severity === "HIGH" ? "#ff444411" : "#ff990011",
                          border: `1px solid ${sig.severity === "HIGH" ? "#ff444433" : "#ff990033"}`
                        }}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                          <span style={{ fontSize: 10, color: "#6677aa", letterSpacing: 1 }}>
                            {sig.threat_type?.replace(/_/g, " ").toUpperCase()}
                          </span>
                          <span style={{
                            fontSize: 9, fontWeight: 700,
                            color: sig.severity === "HIGH" ? "#ff4444" : "#ff9900"
                          }}>{sig.severity}</span>
                        </div>
                        <div style={{ fontSize: 11, color: "#aabbcc", lineHeight: 1.5, marginBottom: 4 }}>
                          {sig.summary}
                        </div>
                        <div style={{ fontSize: 11, color: "#4488ff" }}>→ {sig.action}</div>
                      </motion.div>
                    ))}
                  </>
                )}

                {agriforecast && (
                  <>
                    <div style={{ margin: "16px 0 10px", fontSize: 10, color: "#334466", letterSpacing: 2 }}>
                      AGRI PRICE FORECAST — 7 DAYS
                    </div>
                    <div style={{ padding: 12, background: "#ffffff05", borderRadius: 8, border: "1px solid #0d1530" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
                        <span style={{ fontSize: 11, color: "#6677aa" }}>Current</span>
                        <span style={{ fontSize: 14, fontWeight: 700, color: "#00cc44", fontFamily: "Syne,sans-serif" }}>
                          ₹{agriforecast.current_price?.toLocaleString("en-IN")}
                        </span>
                      </div>
                      {agriforecast.forecasts?.slice(0, 4).map((f, i) => (
                        <div key={i} style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
                          <span style={{ fontSize: 10, color: "#334466" }}>{f.date}</span>
                          <span style={{ fontSize: 11, color: "#aabbcc" }}>₹{f.predicted_price?.toLocaleString("en-IN")}</span>
                        </div>
                      ))}
                      {agriforecast.spike_alert
                        ? <div style={{
                          marginTop: 8, padding: "6px 8px", background: "#ff444411", borderRadius: 6,
                          fontSize: 11, color: "#ff4444"
                        }}>
                          ⚠️ {agriforecast.spike_alert.type} — {agriforecast.spike_alert.change_pct}%
                        </div>
                        : <div style={{ marginTop: 8, fontSize: 11, color: "#00cc44" }}>✅ Prices stable</div>
                      }
                    </div>
                  </>
                )}
              </div>
            )}

            {activeTab === "alerts" && (
              <div>
                {alerts.length === 0
                  ? <div style={{
                    textAlign: "center", padding: 40, color: "#00cc44",
                    background: "#00cc4408", borderRadius: 10, border: "1px solid #00cc4422"
                  }}>
                    ✅ All corridors clear</div>
                  : alerts.map(alert => (
                    <motion.div key={alert.alert_id}
                      initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                      style={{
                        background: "#0a0e1a", borderRadius: 10, padding: 16, marginBottom: 12,
                        borderLeft: `3px solid ${({ HIGH: "#ff4444", MEDIUM: "#ff9900", LOW: "#00cc44" }[alert.severity] || "#4488ff")}`,
                        border: `1px solid #1a2040`
                      }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                        <div>
                          <div style={{ fontSize: 14, fontWeight: 700 }}>{alert.user_name}</div>
                          <div style={{ fontSize: 11, color: "#6677aa" }}>{alert.business}</div>
                        </div>
                        <span style={{
                          fontSize: 10, padding: "2px 8px", borderRadius: 20, fontWeight: 700,
                          background: `${({ HIGH: "#ff4444", MEDIUM: "#ff9900", LOW: "#00cc44" }[alert.severity])}22`,
                          color: { HIGH: "#ff4444", MEDIUM: "#ff9900", LOW: "#00cc44" }[alert.severity]
                        }}>
                          {alert.severity}
                        </span>
                      </div>
                      <div style={{
                        fontSize: 13, color: "#4488ff", lineHeight: 1.7,
                        padding: "8px 10px", background: "#4488ff0a", borderRadius: 6, marginBottom: 8,
                        fontFamily: "Noto Sans Devanagari,sans-serif"
                      }}>{alert.alert_text}</div>
                      {alert.alert_text_english && (
                        <div style={{
                          fontSize: 11, color: "#aabbcc", fontStyle: "italic",
                          marginBottom: 8, lineHeight: 1.6
                        }}>"{alert.alert_text_english}"</div>
                      )}
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#6677aa" }}>
                        <span style={{ color: "#ff9900" }}>
                          ₹{alert.counterfactual_cost_inr?.toLocaleString("en-IN")} at risk
                        </span>
                        <span>🛣️ {alert.highway}</span>
                      </div>
                    </motion.div>
                  ))}
              </div>
            )}

            {activeTab === "corridors" && (
              <div>
                {corridors.map(c => (
                  <motion.div key={c.id} whileHover={{ x: 4 }}
                    onClick={() => {
                      const next = activeCorr === c.id ? null : c.id;
                      setActiveCorr(next);
                      if (next) { fetchAttribution(next); fetchReasoning(next); }
                      setShowRadar(next);
                    }}
                    style={{
                      padding: "14px 16px", borderRadius: 8, marginBottom: 10, cursor: "pointer",
                      background: activeCorr === c.id ? `${c.color}18` : "#ffffff05",
                      border: `1px solid ${activeCorr === c.id ? c.color : "#1a2040"}`
                    }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
                      <div style={{
                        width: 10, height: 10, borderRadius: "50%", background: c.color,
                        boxShadow: `0 0 10px ${c.color}`
                      }} />
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 13, fontWeight: 600 }}>{c.id}</div>
                        <div style={{ fontSize: 10, color: "#6677aa" }}>{c.name}</div>
                      </div>
                      <div style={{ textAlign: "right" }}>
                        <div style={{ fontSize: 16, fontWeight: 700, color: c.color, fontFamily: "Syne,sans-serif" }}>
                          {(c.risk * 100).toFixed(0)}%
                        </div>
                      </div>
                    </div>
                    <div style={{ height: 4, background: "#1a2040", borderRadius: 2, overflow: "hidden", marginBottom: 8 }}>
                      <motion.div animate={{ width: `${c.risk * 100}%` }} transition={{ duration: 1 }}
                        style={{ height: "100%", background: c.color, borderRadius: 2 }} />
                    </div>
                    {/* Show attribution inline when selected */}
                    {activeCorr === c.id && activeAttr && (
                      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                        <div style={{ fontSize: 10, color: "#334466", letterSpacing: 2, marginBottom: 8, marginTop: 4 }}>
                          SIGNAL ATTRIBUTION
                        </div>
                        {Object.entries(activeAttr.components || {}).map(([k, v]) => (
                          <RiskBar key={k} value={v}
                            color={COMPONENT_COLORS[k] || "#4488ff"}
                            label={`${COMPONENT_ICONS[k]} ${(activeAttr.labels || {})[k] || k}`} />
                        ))}
                        <div style={{ display: "flex", justifyContent: "center", marginTop: 12 }}>
                          <RadarChart attribution={activeAttr} size={180} />
                        </div>
                      </motion.div>
                    )}
                  </motion.div>
                ))}
              </div>
            )}

            {activeTab === "users" && (
              <div>
                {users.map((user, i) => (
                  <motion.div key={user.user_id}
                    initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}
                    style={{
                      background: "#ffffff05", border: "1px solid #0d1530",
                      borderRadius: 10, padding: 16, marginBottom: 10
                    }}>
                    <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 12 }}>
                      <div style={{
                        width: 36, height: 36, borderRadius: "50%", background: "#4488ff22",
                        color: "#4488ff", display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: 16, fontWeight: 700, fontFamily: "Syne,sans-serif"
                      }}>
                        {user.name?.charAt(0)}
                      </div>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 700 }}>{user.name}</div>
                        <div style={{ fontSize: 10, color: "#6677aa" }}>{user.business}</div>
                      </div>
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, marginBottom: 8 }}>
                      {[{ l: "Location", v: user.location }, { l: "Channel", v: user.alert_channel },
                      { l: "Language", v: user.language }, { l: "Trust", v: `${(user.trust_score * 100).toFixed(0)}%` }].map(d => (
                        <div key={d.l} style={{ padding: "5px 8px", background: "#ffffff03", borderRadius: 6 }}>
                          <div style={{ fontSize: 9, color: "#334466", marginBottom: 2 }}>{d.l}</div>
                          <div style={{ fontSize: 11, color: "#aabbcc" }}>{d.v}</div>
                        </div>
                      ))}
                    </div>
                    <div style={{ height: 3, background: "#1a2040", borderRadius: 2, overflow: "hidden" }}>
                      <motion.div animate={{ width: `${user.trust_score * 100}%` }}
                        style={{ height: "100%", background: "#4488ff", borderRadius: 2 }} />
                    </div>
                  </motion.div>
                ))}
              </div>
            )}

            {activeTab === "intel" && (
              <div>
                {/* Peak analysis */}
                {peakAnalysis && (
                  <div style={{
                    marginBottom: 14, padding: 14, background: "#ffffff05",
                    borderRadius: 8, border: "1px solid #0d1530"
                  }}>
                    <div style={{ fontSize: 10, color: "#334466", letterSpacing: 2, marginBottom: 10 }}>
                      CORRIDOR DISRUPTION RANKING
                    </div>
                    {peakAnalysis.ranked_corridors?.slice(0, 6).map((corr, i) => (
                      <div key={corr.highway} style={{
                        display: "flex", justifyContent: "space-between",
                        marginBottom: 8, alignItems: "center"
                      }}>
                        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                          <div style={{
                            width: 16, height: 16, borderRadius: "50%",
                            background: riskColor(corr.current_risk) + "33",
                            color: riskColor(corr.current_risk),
                            display: "flex", alignItems: "center", justifyContent: "center",
                            fontSize: 9, fontWeight: 700
                          }}>#{i + 1}</div>
                          <div>
                            <div style={{
                              fontSize: 12, fontWeight: 700,
                              color: riskColor(corr.current_risk)
                            }}>{corr.highway}</div>
                            <div style={{ fontSize: 9, color: "#334466" }}>{corr.route}</div>
                          </div>
                        </div>
                        <div style={{
                          fontSize: 14, fontWeight: 700,
                          color: riskColor(corr.current_risk), fontFamily: "Syne,sans-serif"
                        }}>
                          {(corr.current_risk * 100).toFixed(0)}%
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Selected corridor radar */}
                {activeCorr && activeAttr && (
                  <div style={{
                    marginBottom: 14, padding: 14, background: "#ffffff05",
                    borderRadius: 8, border: "1px solid #4488ff33"
                  }}>
                    <div style={{ fontSize: 10, color: "#334466", letterSpacing: 2, marginBottom: 10 }}>
                      {activeCorr} RISK ATTRIBUTION RADAR
                    </div>
                    <div style={{ display: "flex", justifyContent: "center", marginBottom: 12 }}>
                      <RadarChart attribution={activeAttr} size={200} />
                    </div>
                    {reasoning?.reasoning && !reasoningLoading && (
                      <div>
                        <div style={{ fontSize: 10, color: "#334466", letterSpacing: 2, marginBottom: 8 }}>
                          GEMINI REASONING CHAIN
                        </div>
                        {reasoning.reasoning.reasoning_chain?.map((s, i) => (
                          <div key={i} style={{ display: "flex", gap: 8, marginBottom: 6, alignItems: "flex-start" }}>
                            <div style={{
                              width: 16, height: 16, borderRadius: "50%",
                              background: "#4488ff22", color: "#4488ff",
                              display: "flex", alignItems: "center", justifyContent: "center",
                              fontSize: 9, fontWeight: 700, flexShrink: 0
                            }}>{i + 1}</div>
                            <div style={{ fontSize: 11, color: "#aabbcc", lineHeight: 1.5 }}>{s}</div>
                          </div>
                        ))}
                      </div>
                    )}
                    {reasoningLoading && (
                      <div style={{ fontSize: 11, color: "#334466", textAlign: "center", padding: 10 }}>
                        🧠 Gemini analyzing...
                      </div>
                    )}
                  </div>
                )}

                {/* ML layer status */}
                <div style={{ padding: 14, background: "#ffffff05", borderRadius: 8, border: "1px solid #0d1530" }}>
                  <div style={{ fontSize: 10, color: "#334466", letterSpacing: 2, marginBottom: 10 }}>ML LAYER STATUS</div>
                  {[
                    { l: "XGBoost Disruption", s: "active", v: "2000 samples · 0.87+ AUC" },
                    { l: "Gradient Boost Demand", s: "active", v: "5 commodities · 730-day" },
                    { l: "Gemini NLP Sentiment", s: "active", v: "Real-time news scan" },
                    { l: "Feedback Resonance", s: "active", v: "Federated calibration" },
                    { l: "Delivery Router", s: "active", v: "WhatsApp / SMS / App" },
                    { l: "SQLite User DB", s: "active", v: "Users · Logs · Cycles" },
                  ].map(m => (
                    <div key={m.l} style={{
                      display: "flex", justifyContent: "space-between",
                      marginBottom: 8, alignItems: "flex-start"
                    }}>
                      <div>
                        <div style={{ fontSize: 11, color: "#e0e6f0" }}>{m.l}</div>
                        <div style={{ fontSize: 9, color: "#334466" }}>{m.v}</div>
                      </div>
                      <span style={{
                        fontSize: 9, fontWeight: 700, color: "#00cc44",
                        background: "#00cc4411", padding: "2px 6px", borderRadius: 4
                      }}>
                        {m.s.toUpperCase()}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}