<div dir=rtl>

# Job Tracker: סוכן אחד, שני harnesses

סוכן למעקב אחרי חיפוש עבודה: הוא רושם מועמדויות ומעדכן את הסטטוס שלהן, זוכר העדפות בין סשנים (למשל עבודה היברידית), וקורא מודעות דרושים מהאינטרנט.
הסוכן בנוי פעמיים, כדי להשוות ביניהן:

- **`API/`**: על Messages API הגולמי. את כל ה-harness כתבתי בעצמי: לולאה, כלים, היסטוריה, זיכרון, קונטקסט, compaction, caching ומדידת טוקנים.
- **`SDK/`**: על Claude Agent SDK. Claude Code מריץ את ה-harness, ואני רק מגדירה אותו.

בשתי הגרסאות המודל הוא `claude-opus-5-5` עם effort `medium`. ההשוואה המלאה נמצאת ב-**[REPORT.md](REPORT.md)**.

## תוצאות בקצרה

| | API | SDK |
|---|---|---|
| בדיקות שעברו | 6/6 | 6/6 |
| עלות התרחיש | $0.0422 | $0.0573 |
| אחוז cache | 83.6% | 91.4% |
| קריאות למודל | 13 | 15 |
| שורות harness | 276 | 73 |

## מבנה

```
shared/          קוד הדומיין, משותף לשתי הגרסאות (בלי AI)
  jobs.py          add_application, update_status, search_applications, fetch_job_posting
  preferences.py   save_preference: זיכרון בין סשנים
  scenario.py      הרצת התרחיש, הבדיקות וספירת שורות הקוד
API/
  main.py  agent.py
  harness/         loop, tools, history, memory, context, compaction, caching, tokens
  scratch.py       הלולאה המינימלית בקובץ אחד (שלב ביניים)
SDK/
  main.py  agent.py  tools.py     כל שורה שמחליפה קובץ harness מסומנת "# replaces: <file>"
tests/           בדיקות offline עם client מדומה, בלי מפתח
scenario.json    7 פניות בשני סשנים, ו-6 בדיקות pass/fail
results/         api.json, sdk.json
REPORT.md        הדוח
docs/            המטלה והחלטות הפיתוח
```

## התקנה

Python 3.14. הגרסאות נעולות ב-`requirements.txt`.

```bash
python -m venv .venv
```

```bash
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## הרצה

**בדיקות offline** (בלי מפתח ובלי אינטרנט):

```bash
.venv\Scripts\python.exe -m pytest tests -q
```

**גרסת API.** צריך מפתח מ-Claude Console. מגדירים אותו רק כמשתנה סביבה בטרמינל, אף פעם לא בקוד:

```bash
$env:ANTHROPIC_API_KEY = "<your key>"
```

```bash
.venv\Scripts\python.exe API\main.py --scenario scenario.json --out results/api.json
```

**גרסת SDK.** רצה על ה-login ב-Claude Code, ולא צריך מפתח. אם `ANTHROPIC_API_KEY` מוגדר, `main.py` מסיר אותו להרצה הזו, כדי שהחיוב לא יעבור למפתח:

```bash
.venv\Scripts\python.exe SDK\main.py --scenario scenario.json --out results/sdk.json
```

**שיחה חופשית:** מריצים `API\main.py` או `SDK\main.py` בלי פרמטרים. כדי להמשיך סשן קודם מוסיפים `--session <id>`.

כל הרצת תרחיש מתחילה ממצב נקי ב-`runs/<version>/`. בשיחה חופשית הנתונים נשמרים ב-`data/`, ואפשר לשנות את המיקום עם `JOB_TRACKER_DIR`.

## הערות

- **ההדפסות בזמן ריצה:** ב-API כל פעולה מודפסת עם שם הקובץ שביצע אותה, למשל `[loop.py]` או `[caching.py]`.
- **סינון רשת:** ברשת עם סינון שמחליף תעודות (כמו NetFree), חיבורי HTTPS נבדקים דרך מאגר התעודות של Windows (`truststore`). אתר שחסום בסינון חוזר למודל כשגיאת כלי (`is_error`).

</div>
