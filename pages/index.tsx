import { useState, useEffect } from "react";
import { validateCompleteForm, ValidationResult } from "../lib/validation";
import { EngineerInput } from "../lib/components/EngineerInput";
import { SmartDatePicker } from "../lib/components/SmartDatePicker";
import { WeeksInput } from "../lib/components/WeeksInput";
import { ValidationMessage } from "../lib/components/ValidationMessage";
import { ArtifactPanel } from "../lib/components/ArtifactPanel";
import { LeaveManager } from "../lib/components/LeaveManager";
import { PresetManager } from "../lib/components/PresetManager";
import { AuthWrapper } from "../lib/components/AuthWrapper";
import { 
  useIsArtifactPanelEnabled,
  useIsLeaveManagementEnabled,
  useIsPresetManagerEnabled,
  useMaxWeeksAllowed
} from "../lib/hooks/useFeatureFlags";

export default function Home() {
  const [engineers, setEngineers] = useState("Engineer A, Engineer B, Engineer C, Engineer D, Engineer E, Engineer F");
  const [startSunday, setStartSunday] = useState("");
  const [weeks, setWeeks] = useState(8);
  const [format, setFormat] = useState<"csv" | "xlsx" | "json">("csv");
  const [seeds, setSeeds] = useState({ weekend: 0, chat: 0, oncall: 1, appointments: 2, early: 0 });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formValidation, setFormValidation] = useState<ValidationResult>({ isValid: false, errors: [], warnings: [] });
  const [artifactData, setArtifactData] = useState<any>(null);
  const [showArtifactPanel, setShowArtifactPanel] = useState(false);
  const [leave, setLeave] = useState<Array<{engineer: string, date: string, reason: string}>>([]);

  // Feature flags
  // const { loading: featuresLoading } = useFeatureFlags();
  const isArtifactPanelEnabled = useIsArtifactPanelEnabled();
  const isLeaveManagementEnabled = useIsLeaveManagementEnabled();
  const isPresetManagerEnabled = useIsPresetManagerEnabled();
  const maxWeeksAllowed = useMaxWeeksAllowed();

  // Real-time form validation
  useEffect(() => {
    const payload = {
      engineers: engineers.split(",").map((s: any) => s.trim()).filter(Boolean),
      start_sunday: startSunday,
      weeks,
      seeds,
      leave,
      format
    };
    
    const validation = validateCompleteForm(payload);
    setFormValidation(validation);
  }, [engineers, startSunday, weeks, seeds, format, leave]);

  const handleGenerate = async () => {
    setBusy(true); 
    setError(null);
    
    try {
      // Final validation before submission
      const payload = {
        engineers: engineers.split(",").map((s: any) => s.trim()).filter(Boolean),
        start_sunday: startSunday,
        weeks,
        seeds,
        leave
      };
      
      const validation = validateCompleteForm({ ...payload, format });
      if (!validation.isValid) {
        throw new Error(`Validation failed: ${validation.errors.join(', ')}`);
      }
      
      // Fetch all formats for the artifact panel
      const formats = ['csv', 'xlsx', 'json'];
      const results: any = {};
      
      for (const fmt of formats) {
        const res = await fetch("/api/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ...payload, format: fmt })
        });
        
        if (!res.ok) {
          const txt = await res.text();
          throw new Error(`Failed to generate ${fmt}: ${txt}`);
        }
        
        if (fmt === 'json') {
          results[fmt] = await res.json();
        } else if (fmt === 'xlsx') {
          results[fmt] = await res.blob();
        } else {
          results[fmt] = await res.text();
        }
      }
      
      // Extract fairness report and decision log from JSON if available
      if (results.json) {
        results.fairnessReport = results.json.fairnessReport;
        results.decisionLog = results.json.decisionLog;
      }
      
      setArtifactData(results);
      setShowArtifactPanel(true);
      
    } catch (e: any) {
      setError(e.message || "Generation failed");
    } finally {
      setBusy(false);
    }
  };

  const handleDownloadFormat = (format: 'csv' | 'xlsx' | 'json') => {
    if (!artifactData) return;
    
    const data = artifactData[format];
    if (!data) return;
    
    let blob: Blob;
    let filename: string;
    
    if (format === 'csv') {
      blob = new Blob([data], { type: 'text/csv;charset=utf-8' });
      filename = `schedule-${new Date().toISOString().split('T')[0]}.csv`;
    } else if (format === 'xlsx') {
      blob = data; // Already a blob
      filename = `schedule-${new Date().toISOString().split('T')[0]}.xlsx`;
    } else {
      blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      filename = `schedule-${new Date().toISOString().split('T')[0]}.json`;
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

  const handleApplyPreset = (presetSeeds: any, presetWeeks: number) => {
    setSeeds(presetSeeds);
    setWeeks(presetWeeks);
  };

  return (
    <AuthWrapper requiredRole="EDITOR">
      <div style={{ maxWidth: 800, margin: "40px auto", fontFamily: "Inter, system-ui, Arial" }}>
        <h1>Team Scheduler</h1>
      <p>Week starts on Sunday. Enter exactly 6 engineers with unique names.</p>

      <div style={{ marginBottom: 20 }}>
        <EngineerInput
          value={engineers}
          onChange={setEngineers}
        />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 20 }}>
        <SmartDatePicker
          value={startSunday}
          onChange={setStartSunday}
        />
        <WeeksInput
          value={weeks}
          onChange={setWeeks}
          maxWeeks={maxWeeksAllowed}
        />
      </div>

      <h3 style={{ marginTop: 20 }}>Seeds (fair rotation)</h3>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12 }}>
        {["weekend","chat","oncall","appointments","early"].map((k) => (
          <div key={k}>
            <label>{k}</label>
            <input type="number" min={0} max={5} value={(seeds as any)[k]}
              onChange={e => setSeeds({ ...seeds, [k]: parseInt(e.target.value || "0") })}
              style={{ width: "100%" }}
            />
          </div>
        ))}
      </div>

      {isPresetManagerEnabled && (
        <PresetManager
          currentSeeds={seeds}
          currentWeeks={weeks}
          onApplyPreset={handleApplyPreset}
        />
      )}

      {isLeaveManagementEnabled && (
        <LeaveManager
          engineers={engineers.split(",").map((s: any) => s.trim()).filter(Boolean)}
          leave={leave}
          onChange={setLeave}
          startDate={startSunday}
          weeks={weeks}
        />
      )}

      <h3 style={{ marginTop: 20 }}>Output</h3>
      <div style={{ display: "flex", gap: 12 }}>
        <label><input type="radio" name="fmt" checked={format==="csv"} onChange={() => setFormat("csv")} /> CSV</label>
        <label><input type="radio" name="fmt" checked={format==="xlsx"} onChange={() => setFormat("xlsx")} /> Excel (.xlsx)</label>
        <label><input type="radio" name="fmt" checked={format==="json"} onChange={() => setFormat("json")} /> JSON</label>
      </div>

      <div style={{ marginTop: 20 }}>
        <button 
          onClick={handleGenerate} 
          disabled={busy || !formValidation.isValid} 
          style={{ 
            padding: "12px 20px", 
            fontSize: "16px",
            backgroundColor: formValidation.isValid ? "#3b82f6" : "#9ca3af",
            color: "white",
            border: "none",
            borderRadius: "6px",
            cursor: formValidation.isValid ? "pointer" : "not-allowed",
            opacity: busy ? 0.7 : 1
          }}
        >
          {busy ? "Generating..." : "Generate Schedule"}
        </button>
        
        {artifactData && isArtifactPanelEnabled && (
          <button 
            onClick={() => setShowArtifactPanel(true)}
            style={{ 
              padding: "12px 20px", 
              fontSize: "16px",
              backgroundColor: "#10b981",
              color: "white",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
              marginLeft: "12px"
            }}
          >
            View Artifacts
          </button>
        )}
        
        {!formValidation.isValid && formValidation.errors.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <ValidationMessage errors={["Please fix the validation errors above before generating"]} />
          </div>
        )}
      </div>

      {error && <p style={{ color: "crimson", marginTop: 12 }}>{error}</p>}

      <p style={{ marginTop: 24, fontSize: 12, color: "#555" }}>
        To include leave, call the API directly with a JSON body including a <code>leave</code> array of {"{ Engineer, Date, Reason }"}.
      </p>

      {isArtifactPanelEnabled && (
        <ArtifactPanel
          data={artifactData}
          isVisible={showArtifactPanel}
          onClose={() => setShowArtifactPanel(false)}
          onDownload={handleDownloadFormat}
        />
      )}
      </div>
    </AuthWrapper>
  );
}
