import { useEffect, useMemo, useState } from "react";
import "./Dashboard.css";

const FIELD_CONFIG_KEY = "krishineer_field_config";

const DEFAULT_FIELD_CONFIG = {
  crop_type: 1,
  growth_stage: 2,
  field_area: 2,
  pump_count: 2,
  pump_output: 120,
};

const buildApiBaseUrls = () => {
  const protocol = window.location.protocol || "http:";
  const host = window.location.hostname || "127.0.0.1";
  const ports = [5000, 5001, 5050, 8000];
  const envUrl = process.env.REACT_APP_ML_API_URL;

  const generated = ports.map((port) => `${protocol}//${host}:${port}`);
  const localFallbacks = ports.flatMap((port) => [`http://127.0.0.1:${port}`, `http://localhost:${port}`]);

  return Array.from(new Set([envUrl, ...generated, ...localFallbacks].filter(Boolean)));
};

const fetchWithTimeout = async (url, options = {}, timeoutMs = 6000) => {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
};

const parseJsonSafe = async (response) => {
  const text = await response.text();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return { error: text };
  }
};

const readFieldConfig = () => {
  try {
    const raw = localStorage.getItem(FIELD_CONFIG_KEY);
    if (!raw) return { ...DEFAULT_FIELD_CONFIG };

    const parsed = JSON.parse(raw);
    return {
      crop_type: Number(parsed.crop_type ?? DEFAULT_FIELD_CONFIG.crop_type),
      growth_stage: Number(parsed.growth_stage ?? DEFAULT_FIELD_CONFIG.growth_stage),
      field_area: Number(parsed.field_area ?? DEFAULT_FIELD_CONFIG.field_area),
      pump_count: Number(parsed.pump_count ?? DEFAULT_FIELD_CONFIG.pump_count),
      pump_output: Number(parsed.pump_output ?? DEFAULT_FIELD_CONFIG.pump_output),
    };
  } catch {
    return { ...DEFAULT_FIELD_CONFIG };
  }
};

const generateSevenDayInputs = (fieldConfig) => {
  const baseTemps = [29, 31, 30, 32, 33, 31, 30];
  const baseHumidity = [64, 61, 66, 58, 56, 62, 68];
  const baseRain = [2, 0, 4, 7, 1, 0, 5];
  const baseWind = [10, 12, 11, 14, 13, 10, 9];
  const baseSun = [8.0, 8.5, 7.5, 6.5, 8.8, 9.2, 7.2];

  let soilMoisture = 45;

  return Array.from({ length: 7 }, (_, idx) => {
    const rainfall = Math.max(0, baseRain[idx] + (Math.random() * 2 - 1));
    soilMoisture = soilMoisture - 3.5 + rainfall * 0.35 + (Math.random() * 3 - 1.5);
    soilMoisture = Math.max(15, Math.min(75, soilMoisture));

    return {
      soil_moisture: Number(soilMoisture.toFixed(2)),
      temperature: Number((baseTemps[idx] + (Math.random() * 2 - 1)).toFixed(2)),
      humidity: Number((baseHumidity[idx] + (Math.random() * 4 - 2)).toFixed(2)),
      rainfall_forecast: Number(rainfall.toFixed(2)),
      wind_speed: Number((baseWind[idx] + (Math.random() * 2 - 1)).toFixed(2)),
      sunshine_hours: Number((baseSun[idx] + (Math.random() * 0.8 - 0.4)).toFixed(2)),
      growth_stage: fieldConfig.growth_stage,
      crop_type: fieldConfig.crop_type,
      field_area: fieldConfig.field_area,
    };
  });
};

const AISchedule = () => {
  const [autoMode, setAutoMode] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [scheduleData, setScheduleData] = useState(null);
  const [fieldConfig, setFieldConfig] = useState(() => readFieldConfig());

  const API_BASE_URLS = useMemo(() => buildApiBaseUrls(), []);

  const syncFieldConfigFromStorage = () => {
    const latest = readFieldConfig();
    setFieldConfig(latest);
    return latest;
  };

  useEffect(() => {
    const handleConfigChange = () => {
      syncFieldConfigFromStorage();
    };

    window.addEventListener("storage", handleConfigChange);
    window.addEventListener("focus", handleConfigChange);

    return () => {
      window.removeEventListener("storage", handleConfigChange);
      window.removeEventListener("focus", handleConfigChange);
    };
  }, []);

  const findWorkingApiBase = async () => {
    for (const baseUrl of API_BASE_URLS) {
      try {
        const healthResponse = await fetchWithTimeout(`${baseUrl}/health`, { method: "GET" }, 3000);
        if (healthResponse.ok) {
          return baseUrl;
        }
      } catch {
        // continue probing next base URL
      }
    }
    return null;
  };

  const predictForInput = async (baseUrl, modelInput) => {
    const response = await fetchWithTimeout(
      `${baseUrl}/predict`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(modelInput),
      },
      7000
    );

    const data = await parseJsonSafe(response);
    if (!response.ok) {
      throw new Error(data?.error || `Prediction failed (${response.status})`);
    }

    return {
      liters: Number(data?.water_required_liters || 0),
      rainfallForecast: Number(data?.input?.rainfall_forecast ?? modelInput.rainfall_forecast ?? 0),
    };
  };

  const fetchSchedule = async () => {
    const activeFieldConfig = syncFieldConfigFromStorage();

    if (!Number.isFinite(activeFieldConfig.crop_type) || activeFieldConfig.crop_type < 0 || activeFieldConfig.crop_type > 4) {
      setError("Invalid crop type in Field Configuration.");
      return;
    }

    if (
      !Number.isFinite(activeFieldConfig.growth_stage) ||
      activeFieldConfig.growth_stage < 1 ||
      activeFieldConfig.growth_stage > 4
    ) {
      setError("Invalid growth stage in Field Configuration.");
      return;
    }

    if (!Number.isFinite(activeFieldConfig.field_area) || activeFieldConfig.field_area <= 0) {
      setError("Please set a valid field area in Field Configuration.");
      return;
    }

    if (!Number.isFinite(activeFieldConfig.pump_count) || activeFieldConfig.pump_count <= 0) {
      setError("Please set number of pumps greater than 0 in Field Configuration.");
      return;
    }

    if (!Number.isFinite(activeFieldConfig.pump_output) || activeFieldConfig.pump_output <= 0) {
      setError("Please set pump output greater than 0 in Field Configuration.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const apiBase = await findWorkingApiBase();
      if (!apiBase) {
        throw new Error(
          `ML API is unreachable. Start backend with: python \"ML algo/api/main.py\". Checked: ${API_BASE_URLS.join(", ")}`
        );
      }

      const dailyInputs = generateSevenDayInputs(activeFieldConfig);
      const predictionResults = await Promise.all(
        dailyInputs.map(async (modelInput) => {
          const prediction = await predictForInput(apiBase, modelInput);
          return { modelInput, prediction };
        })
      );

      const start = new Date();
      const schedule = predictionResults.map((item, idx) => {
        const d = new Date(start);
        d.setDate(start.getDate() + idx);
        return {
          day: idx + 1,
          date: d.toISOString().slice(0, 10),
          water_required_liters: Number(item.prediction.liters.toFixed(2)),
          water_required_cubic_meters: Number((item.prediction.liters / 1000).toFixed(3)),
          input: {
            ...item.modelInput,
            rainfall_forecast: item.prediction.rainfallForecast,
          },
        };
      });

      const systemFlowRate = Math.max(1, activeFieldConfig.pump_count * activeFieldConfig.pump_output);

      const todayInput = schedule[0]?.input;
      let todayWaterSavedPercent = 0;
      let todayWaterSavedLiters = 0;
      if (todayInput) {
        const noRainInput = { ...todayInput, rainfall_forecast: 0 };
        const noRainPrediction = await predictForInput(apiBase, noRainInput);
        const baselineNoRainLiters = Number(noRainPrediction.liters || 0);
        const actualLiters = Number(schedule[0].water_required_liters || 0);
        todayWaterSavedLiters = Math.max(0, baselineNoRainLiters - actualLiters);
        if (baselineNoRainLiters > 0) {
          todayWaterSavedPercent = (todayWaterSavedLiters / baselineNoRainLiters) * 100;
          todayWaterSavedPercent = Math.max(0, Math.min(100, todayWaterSavedPercent));
        }
      }

      const total = schedule.reduce((sum, day) => sum + Number(day.water_required_liters || 0), 0);
      setScheduleData({
        schedule_days: 7,
        total_water_liters: Number(total.toFixed(2)),
        total_water_cubic_meters: Number((total / 1000).toFixed(3)),
        average_daily_liters: Number((total / 7).toFixed(2)),
        today_water_saved_percent: Number(todayWaterSavedPercent.toFixed(2)),
        today_water_saved_liters: Number(todayWaterSavedLiters.toFixed(2)),
        today_runtime_saved_minutes: Number((todayWaterSavedLiters / systemFlowRate).toFixed(1)),
        schedule,
      });
    } catch (err) {
      setScheduleData(null);
      setError(err.message || "Unable to fetch data from ML API.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSchedule();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const aiRecommendation = useMemo(() => {
    const firstDay = scheduleData?.schedule?.[0];
    const liters = Number(firstDay?.water_required_liters || 0);
    const systemFlowRate = Math.max(1, (Number(fieldConfig.pump_count) || 0) * (Number(fieldConfig.pump_output) || 0));
    const durationMins = Math.max(1, Math.round(liters / systemFlowRate));

    return {
      time: "6:00 AM",
      duration: `${durationMins} Minutes`,
      waterAmount: `${liters.toLocaleString()} Liters`,
      rainfallForecast: Number(firstDay?.input?.rainfall_forecast || 0).toFixed(2),
      systemFlow: `${systemFlowRate.toLocaleString()} L/min`,
    };
  }, [scheduleData, fieldConfig]);

  const waterSavedToday = useMemo(() => {
    return {
      percent: Number(scheduleData?.today_water_saved_percent || 0).toFixed(2),
      liters: Number(scheduleData?.today_water_saved_liters || 0).toLocaleString(),
      runtimeMin: Number(scheduleData?.today_runtime_saved_minutes || 0).toFixed(1),
    };
  }, [scheduleData]);

  const weeklyPlan =
    scheduleData?.schedule?.map((item) => {
      const date = new Date(item.date);
      const dayName = date.toLocaleDateString("en-US", { weekday: "long" });
      const liters = Number(item.water_required_liters || 0);
      const systemFlowRate = Math.max(1, (Number(fieldConfig.pump_count) || 0) * (Number(fieldConfig.pump_output) || 0));
      const durationMins = Math.max(1, Math.round(liters / systemFlowRate));
      const rain = Number(item?.input?.rainfall_forecast || 0);

      if (liters < 5000 || rain > 15) {
        return {
          day: dayName,
          plan: `Skipped (${rain > 15 ? "Heavy Rain Expected" : "Low Water Need"})`,
        };
      }

      return {
        day: dayName,
        plan: `6:00 AM - ${durationMins} mins (${liters.toLocaleString()} L)`,
      };
    }) || [];

  return (
    <div>
      <h2 className="fw-bold mb-4">AI Irrigation Schedule</h2>

      <div className="schedule-top-grid mb-4">
        <div className="info-card planner-card">
          <h6>AI Planner</h6>
          <p className="planner-caption mb-3">Using latest settings from Field Configuration page.</p>
          <button type="button" className="mode-btn ai-generate-btn" disabled={loading} onClick={fetchSchedule}>
            {loading ? "CALCULATING..." : "GENERATE AI PLAN"}
          </button>
        </div>

        <div className="info-card water-saved-card">
          <h6>Water Saved Today</h6>
          <p className="water-saved-percent">{waterSavedToday.percent}%</p>
          <p className="water-saved-meta">{waterSavedToday.liters} L saved vs no-rain baseline</p>
          <p className="water-saved-meta mb-0">Approx runtime saved: {waterSavedToday.runtimeMin} mins</p>
        </div>
      </div>

      {error && <p className="text-danger fw-bold">{error}</p>}

      <div className="ai-card">
        <h4 className="mb-4">AI Recommendation</h4>

        <div className="ai-grid">
          <div>
            <h6>Recommended Time</h6>
            <p>{aiRecommendation.time}</p>
          </div>

          <div>
            <h6>Duration</h6>
            <p>{aiRecommendation.duration}</p>
          </div>

          <div>
            <h6>Water Amount</h6>
            <p>{aiRecommendation.waterAmount}</p>
          </div>

          <div>
            <h6>Total Pump Output</h6>
            <p>{aiRecommendation.systemFlow}</p>
          </div>
        </div>

        <p className="mt-3 mb-0" style={{ fontWeight: 600, opacity: 0.92, color: "#87CEEB" }}>
          Rainfall Forecast (Today): {aiRecommendation.rainfallForecast} mm
        </p>

        <div className="mt-4">
          <button
            className={`mode-btn ${autoMode ? "active-mode" : ""}`}
            onClick={() => setAutoMode(!autoMode)}
            type="button"
          >
            {autoMode ? "AUTO MODE ENABLED" : "MANUAL MODE"}
          </button>
        </div>
      </div>

      <div className="chart-card mt-4">
        <h3 className="mb-3 fw-bold">Weekly Irrigation Plan</h3>

        {scheduleData && (
          <p className="mb-3">
            Total Water Required: <strong>{Number(scheduleData.total_water_liters || 0).toLocaleString()} L</strong>
          </p>
        )}

        {weeklyPlan.map((item, index) => (
          <div key={index} className="schedule-row">
            <strong>{item.day}</strong>
            <span>{item.plan}</span>
          </div>
        ))}

        {!loading && !error && weeklyPlan.length === 0 && <p className="mb-0">No schedule data available.</p>}
      </div>
    </div>
  );
};

export default AISchedule;
