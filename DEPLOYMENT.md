# Open New Order — Deployment Guide

This is the second app in the `mn-pa-data-extractor` repo. It runs alongside
your existing PA extractor without affecting it.

## What's in this update

**5 files to upload to GitHub:**

| File | Purpose |
|------|---------|
| `new_order_app.py` | Main app — two tabs (Open new order + Order queue) |
| `extractor.py` | Shared extraction logic (mirrors `app.py`) |
| `assignment_rules.py` | Closer → underwriter / office / assistant defaults |
| `supabase_client.py` | DB + storage helpers |
| `requirements.txt` | Updated to add the `supabase` package |

**Files that stay unchanged:**
- `app.py` (your existing extractor — completely untouched)
- `extraction_prompt.py`
- `extraction_schema.json`
- `summary_generator.py`

## Step 1 — Upload to GitHub

In `bctradr/mn-pa-data-extractor` on GitHub:

1. Click **Add file → Upload files**
2. Drag in: `new_order_app.py`, `extractor.py`, `assignment_rules.py`, `supabase_client.py`
3. Drag in `requirements.txt` (it will replace the existing one)
4. Commit message: "Add Open New Order app"
5. Click **Commit changes**

## Step 2 — Deploy as a second Streamlit app

Your existing extractor stays at its current URL. We'll add a second deployment
from the same repo, pointing at `new_order_app.py`.

1. Go to https://share.streamlit.io
2. Click **New app**
3. Repository: `bctradr/mn-pa-data-extractor`
4. Branch: `main`
5. **Main file path: `new_order_app.py`** ← important, not `app.py`
6. Pick a unique URL (e.g. `mn-new-order`)
7. Click **Deploy**

## Step 3 — Configure secrets for the new app

The new app needs three secrets. In Streamlit Cloud, go to the new app's
settings → **Secrets**, and paste:

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
SUPABASE_URL = "https://xxxxxxxxxxxx.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGc..."
```

- `ANTHROPIC_API_KEY` — same key your existing extractor uses
- `SUPABASE_URL` — from Supabase project settings → API → Project URL
- `SUPABASE_SERVICE_KEY` — from Supabase project settings → API → `service_role` key

Click **Save**. The app will restart and pick up the new secrets.

## Step 4 — Verify

Open the new app's URL. You should see:

- **Open new order** tab — file uploader + form fields
- **Order queue** tab — "No orders yet" message

Pick a closer (e.g. Marcy) and confirm:
- Underwriter Code auto-fills with `CT`
- Office auto-fills with `Coon Rapids KW`
- Assistant auto-fills with `Ashley`

Change Order Type to `Seller Side Only` — Assistant should switch to `Sandra`.
Change to `Dual Closing` — Assistant should be `Ashley & Sandra`.

If autofill works, upload a test PDF, fill in the required fields (everything
with `*`), and click **Save Order**. Then check the Order queue tab — your
order should appear. Click the row to expand, then **Extract Fields**.

## Troubleshooting

**"Module not found: supabase"**
The deploy didn't pick up the new `requirements.txt`. In Streamlit Cloud,
click **Manage app** → **Reboot**.

**"Failed to load orders: ..."**
Either the Supabase URL/key is wrong, or the `orders` table doesn't exist.
Re-check the SQL in Supabase's SQL editor (the table-creation query you ran
earlier).

**"Failed to save: ... bucket not found"**
The storage bucket `order-documents` wasn't created. In Supabase → Storage,
click **New bucket**, name it `order-documents` exactly, leave Public OFF.

**The new app shows the OLD app's content**
You set Main file path to `app.py` instead of `new_order_app.py`. In Streamlit
Cloud, click **Manage app** → **Settings** → fix the path → **Save** → reboot.

## After validating an order in TPS

Once you've pushed an order's data to TPS, click the order's row to expand,
scroll to the bottom, and click **🗑️ Delete order**. This removes the order
row, the `order_documents` rows, and deletes the PDFs from Supabase storage —
keeping your free-tier usage under control.
