import pandas as pd
import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error


# LOADING THE DATA
df = pd.read_csv('data/training_data.csv')

FEATURES = [
    'soil_moisture', 'temperature', 'humidity',
    'rainfall_forecast', 'wind_speed', 'sunshine_hours',
    'growth_stage', 'crop_type', 'field_area'
]

TARGET = 'water_required'

X = df[FEATURES]
y = df[TARGET]

print(f"Dataset: {X.shape[0]} rows, {X.shape[1]} features")
print(f"Target range: {y.min():.0f}L to {y.max():.0f}L")
print(f"Target mean:  {y.mean():.0f}L\n")


# TRAIN/TEST SPLIT : 20% TEST DATA, 80% TRAINING DATA
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
print(f"Training on {len(X_train)} samples, testing on {len(X_test)} samples\n")

# TRAINING RANDOM FOREST
print("Training random forest...")
model = RandomForestRegressor(
    n_estimators = 500,
    max_depth = 15,
    min_samples_split = 5,
    min_samples_leaf = 2,
    max_features = 'sqrt',
    random_state = 42,
    n_jobs = -1
)
model.fit(X_train, y_train)
print("Training complete.\n")

# EVALUATION
y_pred = model.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)
rmse = mean_squared_error(y_test, y_pred) ** 0.5
r2 = r2_score(y_test, y_pred)

print("MODEL PERFORMANCE----")
print(f"MAE  (Mean Absolute Error): {mae:,.0f} litres")
print(f"RMSE (Root Mean Sq Error):  {rmse:,.0f} litres")
print(f"R²   (Accuracy score):      {r2:.4f}")
print()

avg_water = y_test.mean()
pct_error = (mae / avg_water) * 100
print(f"Average field water need:   {avg_water:,.0f} litres")
print(f"Model is off by avg:        {pct_error:.1f}% of typical requirement")
print()

# CROSS VALIDATION
print("Running 5-fold cross validation...")
cv_scores = cross_val_score(model,X,y,cv=5,scoring='r2',n_jobs=-1)
print(f"CV R2 SCORES: {[round(s,4) for s in cv_scores]}")
print(f"Mean CV R²:   {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
print()

# FEATURE IMPORTANCE
importances = pd.Series(model.feature_importances_, index=FEATURES)
importances_sorted = importances.sort_values(ascending=False)
for feat, score in importances_sorted.items():
    bar = '█' * int(score * 50)
    print(f"{feat:<22} {score:.4f}  {bar}")
print()

# SANITY CHECK — manual prediction
# A 2-hectare corn field, dry soil, hot day, no rain coming
test_case = pd.DataFrame([{
    'soil_moisture': 25,       # very dry
    'temperature': 38,         # hot
    'humidity': 35,            # low humidity
    'rainfall_forecast': 0,    # no rain
    'wind_speed': 20,          # moderate wind
    'sunshine_hours': 9,       # sunny day
    'growth_stage': 3,         # flowering stage (peak demand)
    'crop_type': 2,            # corn
    'field_area': 2.0          # 2 hectares
}])

prediction = model.predict(test_case)[0]
print("── SANITY CHECK ───────────────────────────")
print(f"Scenario: 2ha corn field, dry + hot + no rain")
print(f"Predicted water required: {prediction:,.0f} litres")
print(f"That's {prediction/1000:.1f} cubic meters")
print()

# ET0 ≈ 7mm, Kc=1.2, stage=1.0 → ET_crop=8.4mm
# net_irrigation ≈ 8.4mm, 2ha field → 8.4 × 2 × 10000 = 168,000L
print(f"Agronomic estimate: ~168,000 litres\n")
print(f"(If prediction is in this range, model learned correctly)\n")

# SAVE
joblib.dump(model, 'model/irrigation_model.pkl')
joblib.dump(FEATURES, 'model/features.pkl')
print("\nModel saved successfully.")

# import pandas as pd
# import numpy as np

# crop_names = {0:'Wheat', 1:'Rice', 2:'Corn', 3:'Cotton', 4:'Sugarcane'}

# print("=" * 60)
# print("  FINAL MODEL VALIDATION")
# print("=" * 60)

# tests = [
#     # GROUP 1: Rainfall must decrease predictions monotonically
#     ("GROUP 1: Rainfall Response (3ha corn, dry soil, fixed everything else)", None, None, None),
#     ("No rain",          0,  150000, 9999999, {'soil_moisture':35,'temperature':33,'humidity':50,'rainfall_forecast':0, 'wind_speed':12,'sunshine_hours':8,'growth_stage':3,'crop_type':2,'field_area':3.0}),
#     ("Light rain (5mm)", 0,  80000, 149999,  {'soil_moisture':35,'temperature':33,'humidity':50,'rainfall_forecast':5, 'wind_speed':12,'sunshine_hours':8,'growth_stage':3,'crop_type':2,'field_area':3.0}),
#     ("Heavy rain (20mm)",0,  0,      60000,  {'soil_moisture':35,'temperature':33,'humidity':50,'rainfall_forecast':20,'wind_speed':12,'sunshine_hours':8,'growth_stage':3,'crop_type':2,'field_area':3.0}),
#     ("Monsoon (35mm)",   0,  0,      25000,  {'soil_moisture':35,'temperature':33,'humidity':50,'rainfall_forecast':35,'wind_speed':12,'sunshine_hours':8,'growth_stage':3,'crop_type':2,'field_area':3.0}),

#     # GROUP 2: Field area must scale predictions linearly
#     ("GROUP 2: Area Scaling (wheat, moderate conditions)", None, None, None),
#     ("1 ha",  0,  15000,  9999999, {'soil_moisture':40,'temperature':30,'humidity':55,'rainfall_forecast':2,'wind_speed':10,'sunshine_hours':7,'growth_stage':2,'crop_type':0,'field_area':1.0}),
#     ("3 ha",  0,  45000,  9999999, {'soil_moisture':40,'temperature':30,'humidity':55,'rainfall_forecast':2,'wind_speed':10,'sunshine_hours':7,'growth_stage':2,'crop_type':0,'field_area':3.0}),
#     ("6 ha",  0,  90000,  9999999, {'soil_moisture':40,'temperature':30,'humidity':55,'rainfall_forecast':2,'wind_speed':10,'sunshine_hours':7,'growth_stage':2,'crop_type':0,'field_area':6.0}),

#     # GROUP 3: Drier soil = more water
#     ("GROUP 3: Soil Moisture Response (2ha corn, no rain)", None, None, None),
#     ("Wet soil (75%)",      0,  0,      15000,  {'soil_moisture':75,'temperature':30,'humidity':60,'rainfall_forecast':0,'wind_speed':10,'sunshine_hours':6,'growth_stage':2,'crop_type':2,'field_area':2.0}),
#     ("Moderate soil (45%)", 0,  15000,  9999999,{'soil_moisture':45,'temperature':30,'humidity':60,'rainfall_forecast':0,'wind_speed':10,'sunshine_hours':6,'growth_stage':2,'crop_type':2,'field_area':2.0}),
#     ("Dry soil (20%)",      0,  40000,  9999999,{'soil_moisture':20,'temperature':30,'humidity':60,'rainfall_forecast':0,'wind_speed':10,'sunshine_hours':6,'growth_stage':2,'crop_type':2,'field_area':2.0}),

#     # GROUP 4: Crop type ranking — Sugarcane > Rice > Corn > Cotton > Wheat
#     ("GROUP 4: Crop Type Ranking (3ha, same conditions)", None, None, None),
#     ("Wheat      — expect LOWEST",    0, 0,      9999999, {'soil_moisture':40,'temperature':32,'humidity':50,'rainfall_forecast':2,'wind_speed':15,'sunshine_hours':8,'growth_stage':3,'crop_type':0,'field_area':3.0}),
#     ("Cotton     — expect 2nd LOWEST",0, 0,      9999999, {'soil_moisture':40,'temperature':32,'humidity':50,'rainfall_forecast':2,'wind_speed':15,'sunshine_hours':8,'growth_stage':3,'crop_type':3,'field_area':3.0}),
#     ("Corn       — expect MIDDLE",    0, 0,      9999999, {'soil_moisture':40,'temperature':32,'humidity':50,'rainfall_forecast':2,'wind_speed':15,'sunshine_hours':8,'growth_stage':3,'crop_type':2,'field_area':3.0}),
#     ("Rice       — expect 2nd HIGHEST",0,0,      9999999, {'soil_moisture':40,'temperature':32,'humidity':50,'rainfall_forecast':2,'wind_speed':15,'sunshine_hours':8,'growth_stage':3,'crop_type':1,'field_area':3.0}),
#     ("Sugarcane  — expect HIGHEST",   0, 0,      9999999, {'soil_moisture':40,'temperature':32,'humidity':50,'rainfall_forecast':2,'wind_speed':15,'sunshine_hours':8,'growth_stage':3,'crop_type':4,'field_area':3.0}),

#     # GROUP 5: Growth stage must follow 1 < 2 < 3 > 4
#     ("GROUP 5: Growth Stage (2ha corn, no rain, dry soil)", None, None, None),
#     ("Stage 1 — Seedling  (LOWEST)",  0, 0,      9999999, {'soil_moisture':40,'temperature':32,'humidity':50,'rainfall_forecast':0,'wind_speed':10,'sunshine_hours':8,'growth_stage':1,'crop_type':2,'field_area':2.0}),
#     ("Stage 2 — Vegetative",          0, 0,      9999999, {'soil_moisture':40,'temperature':32,'humidity':50,'rainfall_forecast':0,'wind_speed':10,'sunshine_hours':8,'growth_stage':2,'crop_type':2,'field_area':2.0}),
#     ("Stage 3 — Flowering (HIGHEST)", 0, 0,      9999999, {'soil_moisture':40,'temperature':32,'humidity':50,'rainfall_forecast':0,'wind_speed':10,'sunshine_hours':8,'growth_stage':3,'crop_type':2,'field_area':2.0}),
#     ("Stage 4 — Harvest",             0, 0,      9999999, {'soil_moisture':40,'temperature':32,'humidity':50,'rainfall_forecast':0,'wind_speed':10,'sunshine_hours':8,'growth_stage':4,'crop_type':2,'field_area':2.0}),

#     # GROUP 6: Absolute extreme scenarios
#     ("GROUP 6: Extreme Scenarios", None, None, None),
#     ("Peak heatwave 10ha corn",       0, 600000, 9999999, {'soil_moisture':15,'temperature':45,'humidity':20,'rainfall_forecast':0, 'wind_speed':20,'sunshine_hours':12,'growth_stage':3,'crop_type':2,'field_area':10.0}),
#     ("Saturated + monsoon (near 0)",  0, 0,      5000,    {'soil_moisture':80,'temperature':22,'humidity':90,'rainfall_forecast':35,'wind_speed':5, 'sunshine_hours':1, 'growth_stage':2,'crop_type':1,'field_area':4.0}),
#     ("Sugarcane large farm dry",      0, 500000, 9999999, {'soil_moisture':25,'temperature':38,'humidity':35,'rainfall_forecast':0, 'wind_speed':18,'sunshine_hours':10,'growth_stage':3,'crop_type':4,'field_area':5.0}),
#     ("Seedling wheat cool day",       0, 0,      25000,   {'soil_moisture':55,'temperature':20,'humidity':70,'rainfall_forecast':3, 'wind_speed':8, 'sunshine_hours':3, 'growth_stage':1,'crop_type':0,'field_area':1.5}),
# ]

# # --- RUN TESTS ---
# passed = 0
# failed = 0
# group_results = []

# for t in tests:
#     if t[1] is None:
#         # It's a group header
#         print(f"\n{'─'*60}")
#         print(f"  {t[0]}")
#         print(f"{'─'*60}")
#         continue

#     name, _, lo, hi, data = t
#     pred = model.predict(pd.DataFrame([data]))[0]
#     ok = lo <= pred <= hi
#     status = "✅" if ok else "❌"
#     if ok: passed += 1
#     else:  failed += 1
#     print(f"  {status} {name:<35} {pred:>10,.0f} L")

# total = passed + failed
# print(f"\n{'='*60}")
# print(f"  SCORE: {passed}/{total} passed", end="  ")
# pct = passed/total*100
# if pct == 100:   print("🏆 PERFECT")
# elif pct >= 85:  print("✅ HACKATHON READY")
# elif pct >= 70:  print("⚠️  ACCEPTABLE")
# else:            print("❌ NEEDS WORK")
# print(f"{'='*60}")

# # --- CROP RANKING (most important visual check) ---
# print("\n── CROP RANKING (must be: Wheat < Cotton < Corn < Rice < Sugarcane)")
# base = {'soil_moisture':40,'temperature':32,'humidity':50,
#         'rainfall_forecast':2,'wind_speed':15,'sunshine_hours':8,
#         'growth_stage':3,'crop_type':3,'field_area':3.0}
# crop_preds = {}
# for cid, cname in crop_names.items():
#     t = base.copy(); t['crop_type'] = cid
#     crop_preds[cname] = model.predict(pd.DataFrame([t]))[0]
# for cname, val in sorted(crop_preds.items(), key=lambda x: x[1]):
#     bar = '█' * int(val/8000)
#     print(f"  {cname:<12} {val:>10,.0f} L  {bar}")

# # --- GROWTH STAGE RANKING ---
# print("\n── GROWTH STAGE (must be: 1 < 2 < 3, and 3 > 4)")
# base2 = {'soil_moisture':40,'temperature':32,'humidity':50,
#          'rainfall_forecast':0,'wind_speed':10,'sunshine_hours':8, 'growth_stage':1,
#          'crop_type':2,'field_area':2.0}
# for s in [1,2,3,4]:
#     t = base2.copy(); t['growth_stage'] = s
#     pred = model.predict(pd.DataFrame([t]))[0]
#     bar = '█' * int(pred/5000)
#     print(f"  Stage {s}  {pred:>10,.0f} L  {bar}")

# # --- AREA SCALING ---
# print("\n── AREA SCALING (each step should roughly double)")
# base3 = {'soil_moisture':40,'temperature':30,'humidity':55,
#          'rainfall_forecast':2,'wind_speed':10,'sunshine_hours':7,
#          'growth_stage':2,'crop_type':0,'field_area':2.0}
# prev = None
# for area in [1.0, 2.0, 4.0, 8.0]:
#     t = base3.copy(); t['field_area'] = area
#     pred = model.predict(pd.DataFrame([t]))[0]
#     ratio = f"  ({pred/prev:.2f}x)" if prev else ""
#     print(f"  {area:.0f} ha  →  {pred:>10,.0f} L{ratio}")
#     prev = pred