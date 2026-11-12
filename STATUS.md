# יומן שינויים

2026-11-12 · Claude Code (Opus 4.6)

* עשינו: הקמת שלד תיעוד — AGENTS.md, CLAUDE.md, PROJECT.md, STATUS.md, docs/data_sources.md, docs/decisions.md, .gitignore
* קבצים ששונו: AGENTS.md, CLAUDE.md, PROJECT.md, STATUS.md, docs/data_sources.md, docs/decisions.md, .gitignore
* מצב עכשיו: שלב 1 (שלד תיעוד) — הושלם. טרם נכתב קוד.
* הבא בתור: אישור מבנה התיעוד ע"י המשתמש, בדיקת זמינות פיד GTFS-Realtime, ואז מעבר לשלב 2.

2026-11-12 · Claude Code (Opus 4.6)

* עשינו: הוספת אזור מיקוד — תל אביב (דן, אגד, מטרופולין)
* קבצים ששונו: PROJECT.md, docs/data_sources.md, docs/decisions.md
* מצב עכשיו: שלב 1 (תיעוד) הושלם עם אזור מיקוד. טרם נכתב קוד.
* הבא בתור: אישור סופי של המבנה, בדיקת זמינות פיד GTFS-Realtime לת"א, מעבר לשלב 2.

2026-11-12 · Claude Code (Opus 4.6)

* עשינו: שלב 2 — פרסור GTFS סטטי. אומת URL, הורד קובץ (138MB), פרסור 6 טבלאות, סינון לאזור ת"א, 7 בדיקות עוברות.
* קבצים ששונו: src/gtfs_parser.py (חדש), tests/test_gtfs_parser.py (חדש), requirements.txt (חדש), docs/data_sources.md (עודכן)
* מצב עכשיו: שלב 2 הושלם. GTFS סטטי נקלט ומאומת. אזהרה אחת: תחנה 37362 מופיעה ב-stop_times אך לא בקובץ stops (כנראה תחנה על גבול ה-bbox).
* הבא בתור: בדיקת זמינות פיד GTFS-Realtime (שלב 3), או ישירות לניתוח headway (שלב 4) אם אין פיד RT.

2026-11-12 · Claude Code (Opus 4.6)

* עשינו: שלב 3 — מקליט זמן אמת. אומת שאין GTFS-RT בישראל, נמצא Open Bus Stride API (הסדנא) כמקור SIRI. נבנה מקליט שדוגם מיקומי רכבים, מסנן לת"א ושומר JSONL. דגימה חיה: 77 מיקומים בת"א מתוך 200. 6 בדיקות עוברות.
* קבצים ששונו: src/rt_recorder.py (חדש), tests/test_rt_recorder.py (חדש), docs/data_sources.md (עודכן)
* מצב עכשיו: שלבים 1-3 הושלמו. קליטת GTFS סטטי ומקליט RT עובדים.
* הבא בתור: שלב 4 — ניתוח headway לקו ותחנה נבחרים.
