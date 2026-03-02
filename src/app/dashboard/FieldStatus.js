import { useEffect, useMemo, useState } from "react";
import "./Dashboard.css";

const FIELD_CONFIG_KEY = "krishineer_field_config";

const readInitialConfig = () => {
  try {
    const raw = localStorage.getItem(FIELD_CONFIG_KEY);
    if (!raw) {
      return {
        crop: "Rice",
        area: "2",
        growth: "Vegetative Stage",
        pumpCount: "2",
        pumpCapacity: "120",
      };
    }

    const parsed = JSON.parse(raw);
    return {
      crop: parsed.crop || "Rice",
      area: String(parsed.field_area ?? parsed.area ?? 2),
      growth: parsed.growth || "Vegetative Stage",
      pumpCount: String(parsed.pump_count ?? parsed.pumpCount ?? 2),
      pumpCapacity: String(parsed.pump_output ?? parsed.pumpCapacity ?? 120),
    };
  } catch {
    return {
      crop: "Rice",
      area: "2",
      growth: "Vegetative Stage",
      pumpCount: "2",
      pumpCapacity: "120",
    };
  }
};

const cropToCode = {
  Wheat: 0,
  Rice: 1,
  Corn: 2,
  Cotton: 3,
  Sugarcane: 4,
};

const growthToCode = {
  Seedling: 1,
  "Vegetative Stage": 2,
  Vegetative: 2,
  Flowering: 3,
  Maturity: 4,
  Harvest: 4,
};

const FieldStatus = () => {
  const initial = useMemo(() => readInitialConfig(), []);
  const [crop, setCrop] = useState(initial.crop);
  const [area, setArea] = useState(initial.area);
  const [growth, setGrowth] = useState(initial.growth);
  const [pumpCount, setPumpCount] = useState(initial.pumpCount);
  const [pumpCapacity, setPumpCapacity] = useState(initial.pumpCapacity);

  const areaValue = Number(area) || 0;
  const totalOutput = (Number(pumpCount) || 0) * (Number(pumpCapacity) || 0);

  useEffect(() => {
    const payload = {
      crop,
      crop_type: cropToCode[crop] ?? 1,
      growth,
      growth_stage: growthToCode[growth] ?? 2,
      field_area: Number(area) || 0,
      pump_count: Number(pumpCount) || 0,
      pump_output: Number(pumpCapacity) || 0,
      updated_at: new Date().toISOString(),
    };

    localStorage.setItem(FIELD_CONFIG_KEY, JSON.stringify(payload));
  }, [crop, area, growth, pumpCount, pumpCapacity]);

  return (
    <div>
      <h2 className="fw-bold mb-4">Field Configuration</h2>

      <div className="info-grid">
        <div className="info-card">
          <h6>Crop Type</h6>
          <select
            className="field-select"
            value={crop}
            onChange={(e) => setCrop(e.target.value)}
          >
            <option>Wheat</option>
            <option>Rice</option>
            <option>Corn</option>
            <option>Cotton</option>
            <option>Sugarcane</option>
          </select>
        </div>

        <div className="info-card">
          <h6>Field Area</h6>
          <div className="input-with-unit">
            <input
              type="number"
              min="0.1"
              step="0.1"
              className="field-input"
              value={area}
              onChange={(e) => setArea(e.target.value)}
              placeholder="Enter area"
            />
            <span className="input-unit">ha</span>
          </div>
          <p className="field-hint mb-0">Total cultivated land in hectares.</p>
        </div>

        <div className="info-card">
          <h6>Growth Stage</h6>
          <select
            className="field-select"
            value={growth}
            onChange={(e) => setGrowth(e.target.value)}
          >
            <option>Seedling</option>
            <option>Vegetative Stage</option>
            <option>Flowering</option>
            <option>Maturity</option>
          </select>
        </div>

        <div className="info-card">
          <h6>Number of Pumps</h6>
          <input
            type="number"
            min="0"
            className="field-input"
            value={pumpCount}
            onChange={(e) => setPumpCount(e.target.value)}
          />
        </div>

        <div className="info-card">
          <h6>Each Pump Output (L/min)</h6>
          <input
            type="number"
            min="0"
            className="field-input"
            value={pumpCapacity}
            onChange={(e) => setPumpCapacity(e.target.value)}
          />
        </div>
      </div>

      <div className="field-visual-card mt-5">
        <h4 className="mb-4">Pump System Overview</h4>

        <div className="health-grid">
          <div>
            <h6>Total Field Area</h6>
            <p>{areaValue} ha</p>
          </div>

          <div>
            <h6>Total Pumps</h6>
            <p>{pumpCount || 0}</p>
          </div>

          <div>
            <h6>Individual Output</h6>
            <p>{pumpCapacity || 0} L/min</p>
          </div>

          <div>
            <h6>Total Output Capacity</h6>
            <p>{totalOutput} L/min</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FieldStatus;
