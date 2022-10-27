# Frontend

The frontend is just a React app.

## Getting Started

1. Install the project:

```bash
cd stretch/frontend
nvm use 16.15.1
npm install
```

2. To automatically rebuild static files, run:

```bash
npm run watch
```

This should create a `build/` folder which is used by the FastAPI application to serve the static site.
