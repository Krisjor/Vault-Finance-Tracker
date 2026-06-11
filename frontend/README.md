# Personal Finance Tracker — Frontend

The React frontend for the Personal Finance Tracker thesis project.

## Stack

- **React 18** with **Vite** for fast dev builds
- **React Router 6** for navigation
- **Tailwind CSS 3** for styling
- **Recharts** for charts (donut, bar, area, line)
- **Lucide React** for icons
- **Axios** for API calls with JWT auto-refresh

## Quick start

```bash
# 1. Install dependencies
npm install

# 2. (Optional) Configure the API base URL
echo "VITE_API_BASE=http://localhost:5000/api" > .env

# 3. Run the dev server
npm run dev
# UI available at http://localhost:5173
```

The Vite dev server proxies `/api/*` to `http://localhost:5000`, so no
extra config is needed when running the backend locally.

## Project layout

```
frontend/
├── index.html
├── package.json
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
├── public/
│   └── favicon.svg
└── src/
    ├── main.jsx                    # Entry point
    ├── App.jsx                     # Top-level routing + auth shell
    ├── index.css                   # Tailwind directives + component classes
    ├── context/
    │   └── AuthContext.jsx         # User state, login/register/logout actions
    ├── services/
    │   └── api.js                  # Axios client with JWT interceptor + refresh
    ├── components/
    │   ├── Layout/
    │   │   ├── Sidebar.jsx         # Persistent nav
    │   │   └── PageHeader.jsx      # Reused page title block
    │   └── UI/
    │       ├── Modal.jsx           # Reusable dialog
    │       └── Toast.jsx           # Toast + Alert primitives
    ├── pages/
    │   ├── Login.jsx
    │   ├── Register.jsx
    │   ├── Dashboard.jsx
    │   ├── Accounts.jsx
    │   ├── Transactions.jsx
    │   ├── Budgets.jsx
    │   ├── Goals.jsx
    │   ├── Reports.jsx
    │   ├── Categories.jsx
    │   ├── Import.jsx
    │   └── Settings.jsx
    └── utils/
        ├── format.js               # Currency / number / percent helpers
        └── dates.js                # Date helpers
```

## Design

- **Type**: Instrument Serif for display headings, Inter for body, JetBrains
  Mono for tabular data.
- **Palette**: monochrome ink (slate 50→950) with a single amber accent
  (`accent-400` / `#fbbf24`) used sparingly to anchor the eye.
- **Components**: hand-rolled Tailwind primitives (`card`, `btn-primary`,
  `input`, `label`, etc.) defined in `index.css`. Avoids the ceremony of a
  full component library while keeping styles consistent.

## Build

```bash
npm run build
# Outputs to dist/. Serve as static files behind a reverse proxy or copy to
# the Flask `static/` folder for a single-origin deployment.
```
