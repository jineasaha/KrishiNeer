import pandas as pd
import numpy as np

np.random.seed(42)
N = 8000

# --- FEATURE GENERATION ---
soil_moisture  = np.random.uniform(10, 80, N)
temperature    = np.random.uniform(15, 45, N)
humidity       = np.random.uniform(20, 90, N)
wind_speed     = np.random.uniform(0, 50, N)
sunshine_hours = np.random.uniform(2, 12, N)
growth_stage   = np.random.randint(1, 5, N)
crop_type      = np.random.randint(0, 5, N)
field_area     = np.random.uniform(0.5, 10.0, N)

# --- RAINFALL ---
rainfall_forecast = np.random.exponential(scale=3.0, size=N)
rainfall_forecast = np.clip(rainfall_forecast, 0, 40)

# --- CROP COEFFICIENTS ---
# Wide spread so model is forced to learn crop_type matters
# 0=Wheat, 1=Rice, 2=Corn, 3=Cotton, 4=Sugarcane
Kc_values = {0: 0.70, 1: 1.50, 2: 1.20, 3: 0.80, 4: 1.65}
Kc = np.array([Kc_values[c] for c in crop_type])

# --- GROWTH STAGE MULTIPLIERS ---
# Wide spread so Stage 1 vs Stage 3 is very distinguishable
stage_multiplier = {1: 0.30, 2: 0.70, 3: 1.00, 4: 0.55}
stage_mult = np.array([stage_multiplier[s] for s in growth_stage])

# --- ET0 ---
temp_ET     = ((temperature - 15) / 30) * 6 + 3   # 3 to 9 mm
sun_ET      = ((sunshine_hours - 2) / 10) * 3 + 0.5  # 0.5 to 3.5 mm
wind_ET     = (wind_speed / 50) * 2.5             # 0 to 2.5 mm
humidity_ET = -((humidity - 20) / 70) * 2.0 - 0.5 # -0.5 to -2.5 mm

ET0 = temp_ET + sun_ET + wind_ET + humidity_ET
ET0 = np.clip(ET0, 0.5, 15.0)  # raised ceiling to 15

# --- ET_crop ---
# Range now: 0.5×0.70×0.30 = 0.1mm  to  15×1.65×1.0 = 24.75mm
# This 247x range gives the model very strong signals to learn from
ET_crop = ET0 * Kc * stage_mult

print(f"ET0    → Min:{ET0.min():.1f}  Mean:{ET0.mean():.1f}  Max:{ET0.max():.1f}")
print(f"ETcrop → Min:{ET_crop.min():.2f}  Mean:{ET_crop.mean():.2f}  Max:{ET_crop.max():.2f}")

# --- SOIL MOISTURE DEFICIT ---
FC = 60.0
soil_deficit_fraction = np.clip((FC - soil_moisture) / FC, 0, 1)

# --- EFFECTIVE RAINFALL ---
effective_rain = rainfall_forecast * 0.75

# --- NET IRRIGATION (mm) ---
net_irrigation_mm = np.clip(
    (ET_crop - effective_rain) * (0.5 + 0.5 * soil_deficit_fraction),
    0, None
)

print(f"Net mm → Min:{net_irrigation_mm.min():.2f}  Mean:{net_irrigation_mm.mean():.2f}  Max:{net_irrigation_mm.max():.2f}")
print(f"Non-zero rows: {(net_irrigation_mm > 0).sum()} / {N}")

# --- CONVERT TO LITRES ---
water_required = net_irrigation_mm * field_area * 10000

noise = np.random.normal(0, 500, N)
water_required = np.clip(water_required + noise, 0, None)
water_required = np.round(water_required, 1)
water_required[soil_moisture >= FC] = 0.0

print(f"Water  → Min:{water_required.min():.0f}  Mean:{water_required.mean():.0f}  Max:{water_required.max():.0f}")
print(f"Zero rows: {(water_required == 0).sum()} / {N}")

# --- BUILD DATAFRAME ---
df = pd.DataFrame({
    'soil_moisture':     soil_moisture,
    'temperature':       temperature,
    'humidity':          humidity,
    'rainfall_forecast': rainfall_forecast,
    'wind_speed':        wind_speed,
    'sunshine_hours':    sunshine_hours,
    'growth_stage':      growth_stage,
    'crop_type':         crop_type,
    'field_area':        field_area,
    'water_required':    water_required
})

# --- AUGMENT: explicit zero cases (scaled up with N) ---
N_zero = 800
zero_rows = pd.DataFrame({
    'soil_moisture':     np.random.uniform(55, 80, N_zero),
    'temperature':       np.random.uniform(15, 35, N_zero),
    'humidity':          np.random.uniform(60, 90, N_zero),
    'rainfall_forecast': np.random.uniform(10, 40, N_zero),
    'wind_speed':        np.random.uniform(0, 20, N_zero),
    'sunshine_hours':    np.random.uniform(2, 6, N_zero),
    'growth_stage':      np.random.randint(1, 5, N_zero),
    'crop_type':         np.random.randint(0, 5, N_zero),
    'field_area':        np.random.uniform(0.5, 10.0, N_zero),
    'water_required':    np.zeros(N_zero)
})

df = pd.concat([df, zero_rows], ignore_index=True)
df = df.sample(frac=1, random_state=42).reset_index(drop=True)

df.to_csv('data/training_data.csv', index=False)
print(f"\nDataset saved: {len(df)} rows")
print(df['water_required'].describe().round(1))