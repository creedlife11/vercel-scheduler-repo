import { useState, useEffect } from "react";
import { validateCompleteForm, ValidationResult } from "../lib/validation";

export default function SimplePage() {
  const [engineers, setEngineers] = useState("Engineer A, Engineer B, Engineer C, Engineer D, Engineer E, Engineer F");
  const [startSunday, setStartSunday] = useState("");
  const [weeks, setWeeks] = useState(8);
  const [format, setFormat] = useState<"csv" | "xlsx" | "json">("csv");
  const [seeds, setSeeds] = useState({ weekend: 0, chat: 0, oncall: 1, appointments: 2, early: 0 });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [formValidation, setFormValidation] = useState<ValidationResult>({ isValid: false, errors: [], warnings: [] });

  // Real-time form validation
  useEffect(() => {
    const payload = {
      engineers: engineers.split(",").map((s: any) => s.trim()).filter(Boolean),
      start_sunday: startSunday,
      weeks,
      seeds,
      leave: [],
      format
    };
    
    const validation = validateCompleteForm(payload);
    setFormValidation(validation);
  }, [engineers, startSunday, weeks, seeds, format]);

  const handleGenerate = async () => {
    setBusy(true); 
    setError(null);
    setResult(null);
    
    try {
      const payload = {
        engineers: engineers.split(",").map((s: any) => s.trim()).filter(Boolean),
        start_sunday: startSunday,
        weeks,
        seeds,
        leave: [],
        format
      };
      
      const validation = validateCompleteForm(payload);
      if (!validation.isValid) {
        throw new Error(`Validation failed: ${validation.errors.join(', ')}`);
      }
      
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(`Failed to generate: ${txt}`);
      }
      
      if (format === 'json') {
        const data = await res.json();
        setResult(JSON.stringify(data, null, 2));
      } else {
        const data = await res.text();
        setResult(data);
      }
      
    } catch (e: any) {
      setError(e.message || "Generation failed");
    } finally {
      setBusy(false);
    }
  };

  const handleDownload = () => {
    if (!result) return;
    
    let blob: Blob;
    let filename: string;
    
    if (format === 'csv') {
      blob = new Blob([result], { type: 'text/csv;charset=utf-8' });
      filename = `schedule-${new Date().toISOString().split('T')[0]}.csv`;
    } else if (format === 'json') {
      blob = new Blob([result], { type: 'application/json' });
      filename = `schedule-${new Date().toISOString().split('T')[0]}.json`;
    } else {
      blob = new Blob([result], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      filename = `schedule-${new Date().toISOString().split('T')[0]}.xlsx`;
    }
    
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div style={{ 
      maxWidth: 800, 
      margin: "40px auto", 
      padding: "20px",
      fontFamily: "Inter, system-ui, Arial",
      backgroundColor: "white",
      borderRadius: "8px",
      boxShadow: "0 2px 10px rgba(0,0,0,0.1)"
    }}>
      <h1 style={{ color: "#1f2937", marginBottom: "8px" }}>Enhanced Team Scheduler</h1>
      <p style={{ color: "#6b7280", marginBottom: "24px" }}>
        Week starts on Sunday. Enter exactly 6 engineers with unique names.
      </p>

      <div style={{ marginBottom: 20 }}>
        <label style={{ display: "block", marginBottom: "8px", fontWeight: "500" }}>Engineers</label>
        <input
          type="text"
          value={engineers}
          onChange={(e) => setEngineers(e.target.value)}
          placeholder="Engineer A, Engineer B, Engineer C, Engineer D, Engineer E, Engineer F"
          style={{
            width: "100%",
            padding: "8px 12px",
            border: "1px solid #d1d5db",
            borderRadius: "6px",
            fontSize: "14px"
          }}
        />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 20 }}>
        <div>
          <label style={{ display: "block", marginBottom: "8px", fontWeight: "500" }}>Start Date (Sunday)</label>
          <input
            type="date"
            value={startSunday}
            onChange={(e) => setStartSunday(e.target.value)}
            style={{
              width: "100%",
              padding: "8px 12px",
              border: "1px solid #d1d5db",
              borderRadius: "6px",
              fontSize: "14px"
            }}
          />
        </div>
        <div>
          <label style={{ display: "block", marginBottom: "8px", fontWeight: "500" }}>Weeks</label>
          <input
            type="number"
            min={1}
            max={52}
            value={weeks}
            onChange={(e) => setWeeks(parseInt(e.target.value) || 1)}
            style={{
              width: "100%",
              padding: "8px 12px",
              border: "1px solid #d1d5db",
              borderRadius: "6px",
              fontSize: "14px"
            }}
          />
        </div>
      </div>

      <h3 style={{ marginTop: 20, marginBottom: 12 }}>Seeds (fair rotation)</h3>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12, marginBottom: 20 }}>
        {["weekend","chat","oncall","appointments","early"].map((k) => (
          <div key={k}>
            <label style={{ display: "block", marginBottom: "4px", fontSize: "14px" }}>{k}</label>
            <input 
              type="number" 
              min={0} 
              max={5} 
              value={(seeds as any)[k]}
              onChange={e => setSeeds({ ...seeds, [k]: parseInt(e.target.value || "0") })}
              style={{ 
                width: "100%",
                padding: "6px 8px",
                border: "1px solid #d1d5db",
                borderRadius: "4px",
                fontSize: "14px"
              }}
            />
          </div>
        ))}
      </div>

      <h3 style={{ marginTop: 20, marginBottom: 12 }}>Output Format</h3>
      <div style={{ display: "flex", gap: 16, marginBottom: 20 }}>
        <label style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <input type="radio" name="fmt" checked={format==="csv"} onChange={() => setFormat("csv")} />
          CSV
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <input type="radio" name="fmt" checked={format==="xlsx"} onChange={() => setFormat("xlsx")} />
          Excel (.xlsx)
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <input type="radio" name="fmt" checked={format==="json"} onChange={() => setFormat("json")} />
          JSON
        </label>
      </div>

      {!formValidation.isValid && formValidation.errors.length > 0 && (
        <div style={{ 
          padding: "12px", 
          backgroundColor: "#fef2f2", 
          border: "1px solid #fecaca",
          borderRadius: "6px",
          marginBottom: "16px"
        }}>
          <h4 style={{ margin: "0 0 8px 0", color: "#dc2626" }}>Validation Errors:</h4>
          <ul style={{ margin: 0, paddingLeft: "20px", color: "#dc2626" }}>
            {formValidation.errors.map((error, i) => (
              <li key={i}>{error}</li>
            ))}
          </ul>
        </div>
      )}

      <div style={{ marginBottom: 20 }}>
        <button 
          onClick={handleGenerate} 
          disabled={busy || !formValidation.isValid} 
          style={{ 
            padding: "12px 24px", 
            fontSize: "16px",
            backgroundColor: formValidation.isValid ? "#3b82f6" : "#9ca3af",
            color: "white",
            border: "none",
            borderRadius: "6px",
            cursor: formValidation.isValid ? "pointer" : "not-allowed",
            opacity: busy ? 0.7 : 1,
            marginRight: "12px"
          }}
        >
          {busy ? "Generating..." : "Generate Schedule"}
        </button>
        
        {result && (
          <button 
            onClick={handleDownload}
            style={{ 
              padding: "12px 24px", 
              fontSize: "16px",
              backgroundColor: "#10b981",
              color: "white",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer"
            }}
          >
            Download {format.toUpperCase()}
          </button>
        )}
      </div>

      {error && (
        <div style={{ 
          padding: "12px", 
          backgroundColor: "#fef2f2", 
          border: "1px solid #fecaca",
          borderRadius: "6px",
          color: "#dc2626",
          marginBottom: "16px"
        }}>
          {error}
        </div>
      )}

      {result && (
        <div style={{ marginTop: 20 }}>
          <h3>Generated Schedule</h3>
          <pre style={{ 
            backgroundColor: "#f9fafb", 
            padding: "16px", 
            borderRadius: "6px", 
            overflow: "auto", 
            fontSize: "12px",
            border: "1px solid #e5e7eb",
            maxHeight: "400px"
          }}>
            {result}
          </pre>
        </div>
      )}

      <div style={{ 
        marginTop: 32, 
        padding: "16px", 
        backgroundColor: "#f0f9ff", 
        borderRadius: "6px",
        fontSize: "14px",
        color: "#0369a1"
      }}>
        <h4 style={{ margin: "0 0 8px 0" }}>✨ Enhanced Features Available:</h4>
        <ul style={{ margin: 0, paddingLeft: "20px" }}>
          <li>Fairness analysis and reporting</li>
          <li>Decision logging for transparency</li>
          <li>Multiple export formats (CSV, Excel, JSON)</li>
          <li>Advanced validation and error handling</li>
          <li>Real-time form validation</li>
        </ul>
      </div>
    </div>
  );
}