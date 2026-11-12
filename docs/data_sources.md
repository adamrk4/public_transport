# מקורות נתונים

## GTFS סטטי — משרד התחבורה
- **URL:** https://gtfs.mot.gov.il/gtfsfiles/israel-public-transportation.zip ✅ אומת 2026-11-12
- **פורמט:** GTFS (zip עם CSV) — 138 MB, 36 סוכנויות, 8,079 קווים, 35,402 תחנות
- **רישוי:** טרם אומת (נתונים פתוחים של משרד התחבורה)
- **תדירות עדכון:** טרם אומת
- **אזור מיקוד:** תל אביב — סינון לפי bbox (32.0-32.15°N, 34.74-34.85°E) → 2,268 קווים, 2,631 תחנות

## נתוני זמן אמת — SIRI דרך Open Bus Stride API
- **URL:** https://open-bus-stride-api.hasadna.org.il ✅ אומת 2026-11-12
- **פורמט:** REST API (JSON), מבוסס SIRI שנאסף ע"י פרויקט Open Bus של הסדנא
- **רישוי:** ציבורי, ללא מפתח API
- **תדירות עדכון:** snapshots כל ~דקה (SIRI-SM מהמשרד)
- **endpoints עיקריים:**
  - `siri_vehicle_locations/list` — מיקומי רכבים (lat, lon, bearing, velocity)
  - `siri_rides/list` — נסיעות SIRI
  - `stop_arrivals/list` — הגעות לתחנות
- **הערות:** אין פיד GTFS-Realtime רשמי בישראל. משרד התחבורה מפרסם SIRI-SM, והסדנא אוספת ומנגישה. דגימה הוחזרה בהצלחה (77/200 מיקומים בת"א).

## GTFS-Realtime — לא קיים
משרד התחבורה לא מפרסם פיד GTFS-RT. ראו https://github.com/organicmaps/gtfs-osm-matcher/issues/170
