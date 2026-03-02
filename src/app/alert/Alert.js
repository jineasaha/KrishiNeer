"use client";
import React, { useState } from "react";
import "./alert.css";

export default function Alert() {

  const initialAlerts = [
    {
      id: 1,
      crop: "Cotton",
      message: "Low Soil Moisture",
      current: "18%",
      threshold: "25%",
      severity: "critical",
      time: "02 March 2026 - 10:45 AM"
    },
    {
      id: 2,
      crop: "Sugarcane",
      message: "High Water Level Detected",
      current: "78%",
      threshold: "70%",
      severity: "warning",
      time: "02 March 2026 - 09:30 AM"
    },
    {
      id: 3,
      crop: "Rice",
      message: "Rain Forecast - Irrigation Paused",
      current: "-",
      threshold: "-",
      severity: "info",
      time: "01 March 2026 - 06:15 PM"
    }
  ];

  const [alerts, setAlerts] = useState(initialAlerts);
  const [filter, setFilter] = useState("all");

  const handleResolve = (id) => {
    setAlerts(alerts.filter(alert => alert.id !== id));
  };

  const filteredAlerts =
    filter === "all"
      ? alerts
      : alerts.filter(alert => alert.severity === filter);

  const criticalCount = alerts.filter(a => a.severity === "critical").length;
  const warningCount = alerts.filter(a => a.severity === "warning").length;
  const infoCount = alerts.filter(a => a.severity === "info").length;

  return (
    <div className="alert-container">
      <h1>🚨 Alert Dashboard</h1>

      {/* Summary Section */}
      <div className="alert-summary">
        <div className="summary-card critical">
          <h2>{criticalCount}</h2>
          <p>Critical Alerts</p>
        </div>
        <div className="summary-card warning">
          <h2>{warningCount}</h2>
          <p>Warnings</p>
        </div>
        <div className="summary-card info">
          <h2>{infoCount}</h2>
          <p>Information</p>
        </div>
      </div>

      {/* Filter Buttons */}
      <div className="filter-bar">
        <button className="filter-btn" onClick={() => setFilter("all")}>All</button>
        <button className="filter-btn" onClick={() => setFilter("critical")}>Critical</button>
        <button className="filter-btn" onClick={() => setFilter("warning")}>Warning</button>
        <button className="filter-btn" onClick={() => setFilter("info")}>Info</button>
      </div>

      {/* Alert List */}
      <div className="alert-list">
        {filteredAlerts.length === 0 ? (
          <p style={{ textAlign: "center" }}>No alerts available 🎉</p>
        ) : (
          filteredAlerts.map(alert => (
            <div key={alert.id} className={`alert-card ${alert.severity}`}>
              <div className="alert-details">
                <h3>⚠ {alert.crop} - {alert.message}</h3>
                <p>
                  Current: {alert.current} | Threshold: {alert.threshold}
                </p>
                <span className="alert-time">{alert.time}</span>
              </div>

              <button
                className="resolve-btn"
                onClick={() => handleResolve(alert.id)}
              >
                Mark Resolved
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}