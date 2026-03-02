import react from "react";

import "./overview.css";

export default function CropsOverview() {
  return (
    <section className="crops-container">
      <h1>Crops Overview</h1>
      <p className="intro">
        Our Intelligent Water Optimization System adapts irrigation strategies 
        based on crop type, soil condition, and environmental factors to ensure 
        optimal growth and water efficiency.
      </p>

      <div className="crop-grid">

        <div className="crop-card">
          <h2>🌾 Rice</h2>
          <p><strong>Water Requirement:</strong> High</p>
          <p><strong>Ideal Soil:</strong> Clayey soil</p>
          <p><strong>Irrigation Strategy:</strong> Controlled flooding with moisture monitoring.</p>
        </div>

        <div className="crop-card">
          <h2>🌽 Maize</h2>
          <p><strong>Water Requirement:</strong> Moderate</p>
          <p><strong>Ideal Soil:</strong> Well-drained loamy soil</p>
          <p><strong>Irrigation Strategy:</strong> Drip irrigation based on root-zone moisture.</p>
        </div>

        <div className="crop-card">
          <h2>🍅 Tomato</h2>
          <p><strong>Water Requirement:</strong> Moderate</p>
          <p><strong>Ideal Soil:</strong> Sandy loam</p>
          <p><strong>Irrigation Strategy:</strong> Precise drip irrigation to prevent overwatering.</p>
        </div>

        <div className="crop-card">
          <h2>🌱 Wheat</h2>
          <p><strong>Water Requirement:</strong> Low to Moderate</p>
          <p><strong>Ideal Soil:</strong> Well-drained fertile soil</p>
          <p><strong>Irrigation Strategy:</strong> Scheduled irrigation during critical growth stages.</p>
        </div>

        <div className="crop-card">
            <h2>🌿 Cotton</h2>  
            <p><strong>Water Requirement:</strong> Moderate</p>
            <p><strong>Ideal Soil:</strong> Well-drained black cotton soil (Regur)</p>      
            <p><strong>Irrigation Strategy:</strong> Drip irrigation during flowering stage and Boll development stage</p>     
        </div>    

        <div className="crop-card">
            <h2>🌾 Sugarcane</h2>  
            <p><strong>Water Requirement:</strong> Very high</p>
            <p><strong>Ideal Soil:</strong> Deep well-drained loamy soil</p>      
            <p><strong>Irrigation Strategy:</strong> Drip irrigation with fertigation</p>     
        </div> 
      </div>
    </section>
  );
}
