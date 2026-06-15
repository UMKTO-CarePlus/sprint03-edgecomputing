from datetime import datetime
import os

import requests
from flask import Flask, jsonify, render_template_string, request


FIWARE_HOST = os.getenv("FIWARE_HOST", "34.69.120.192")
STH_COMET_URL = os.getenv("STH_COMET_URL", f"http://{FIWARE_HOST}:8666").rstrip("/")
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8080"))
FIWARE_SERVICE = os.getenv("FIWARE_SERVICE", "openiot")
FIWARE_SERVICE_PATH = os.getenv("FIWARE_SERVICE_PATH", "/")
ENTITY_ID = os.getenv("ENTITY_ID", "CarePlusMission:totem001")
ENTITY_TYPE = os.getenv("ENTITY_TYPE", "CarePlusWalkingMission")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15"))

TRACKED_ATTRIBUTES = [
    "steps",
    "distanceMeters",
    "distanceKm",
    "points",
    "validationStatus",
    "totemId",
    "missionId",
    "userId",
]

HEADERS = {
    "fiware-service": FIWARE_SERVICE,
    "fiware-servicepath": FIWARE_SERVICE_PATH,
}

app = Flask(__name__)


def fiware_get(url):
    response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def parse_value(value):
    if value is None:
        return None

    try:
        if isinstance(value, str) and "." in value:
            return float(value)
        return int(value)
    except (TypeError, ValueError):
        try:
            return float(value)
        except (TypeError, ValueError):
            return value


def get_orion_entity():
    url = f"http://{FIWARE_HOST}:1026/v2/entities/{ENTITY_ID}?options=keyValues"
    return fiware_get(url)


def get_sth_attribute(attribute, last_n=100):
    url = (
        f"{STH_COMET_URL}/STH/v1/contextEntities/type/{ENTITY_TYPE}"
        f"/id/{ENTITY_ID}/attributes/{attribute}?lastN={last_n}"
    )
    data = fiware_get(url)
    responses = data.get("contextResponses", [])
    if not responses:
        return []

    attributes = responses[0].get("contextElement", {}).get("attributes", [])
    if not attributes:
        return []

    rows = []
    for item in attributes[0].get("values", []):
        rows.append(
            {
                "recvTime": item.get("recvTime") or item.get("recvTimeTs"),
                "attribute": attribute,
                "value": parse_value(item.get("attrValue")),
            }
        )
    return rows


def build_history(last_n=100):
    rows_by_time = {}
    errors = {}

    for attribute in TRACKED_ATTRIBUTES:
        try:
            points = get_sth_attribute(attribute, last_n=last_n)
        except requests.RequestException as exc:
            errors[attribute] = str(exc)
            continue

        for point in points:
            recv_time = point["recvTime"]
            if not recv_time:
                continue

            row = rows_by_time.setdefault(recv_time, {"recvTime": recv_time})
            row[attribute] = point["value"]

    rows = list(rows_by_time.values())
    for row in rows:
        distance_meters = row.get("distanceMeters")
        if isinstance(distance_meters, (int, float)) and not row.get("distanceKm"):
            row["distanceKm"] = round(distance_meters / 1000, 3)

    rows.sort(key=lambda row: row["recvTime"])
    return rows, errors


def latest_values(history):
    latest = {}
    for row in history:
        latest["lastRecvTime"] = row.get("recvTime")
        for attribute in TRACKED_ATTRIBUTES:
            if attribute in row and row[attribute] is not None:
                latest[attribute] = row[attribute]

    distance_meters = latest.get("distanceMeters")
    if isinstance(distance_meters, (int, float)) and not latest.get("distanceKm"):
        latest["distanceKm"] = round(distance_meters / 1000, 3)

    return latest


@app.get("/")
def index():
    return render_template_string(
        DASHBOARD_HTML,
        entity_id=ENTITY_ID,
        entity_type=ENTITY_TYPE,
        fiware_host=FIWARE_HOST,
        sth_comet_url=STH_COMET_URL,
        dashboard_port=DASHBOARD_PORT,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


@app.get("/api/health")
def api_health():
    checks = {}
    for name, url in [
        ("orion", f"http://{FIWARE_HOST}:1026/version"),
        ("sthComet", f"{STH_COMET_URL}/version"),
    ]:
        try:
            data = fiware_get(url)
            checks[name] = {"ok": True, "url": url, "data": data}
        except requests.RequestException as exc:
            checks[name] = {"ok": False, "url": url, "error": str(exc)}

    return jsonify(
        {
            "service": "careplus-dashboard",
            "fiwareHost": FIWARE_HOST,
            "sthCometUrl": STH_COMET_URL,
            "dashboardPort": DASHBOARD_PORT,
            "entityId": ENTITY_ID,
            "entityType": ENTITY_TYPE,
            "checks": checks,
        }
    )


@app.get("/api/entity")
def api_entity():
    try:
        return jsonify({"ok": True, "data": get_orion_entity()})
    except requests.RequestException as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502


@app.get("/api/history")
def api_history():
    last_n = request.args.get("lastN", default=100, type=int)
    last_n = max(1, min(last_n, 1000))
    history, errors = build_history(last_n=last_n)

    return jsonify(
        {
            "ok": not errors,
            "entityId": ENTITY_ID,
            "entityType": ENTITY_TYPE,
            "lastN": last_n,
            "attributes": TRACKED_ATTRIBUTES,
            "latest": latest_values(history),
            "history": history,
            "errors": errors,
        }
    )


@app.get("/api/history/<attribute>")
def api_history_attribute(attribute):
    if attribute not in TRACKED_ATTRIBUTES:
        return jsonify({"ok": False, "error": "Unknown attribute"}), 404

    last_n = request.args.get("lastN", default=100, type=int)
    last_n = max(1, min(last_n, 1000))

    try:
        points = get_sth_attribute(attribute, last_n=last_n)
        return jsonify({"ok": True, "attribute": attribute, "lastN": last_n, "history": points})
    except requests.RequestException as exc:
        return jsonify({"ok": False, "error": str(exc)}), 502


DASHBOARD_HTML = """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CarePlus Sprint 03 - Dashboard FIWARE</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {
      color-scheme: light;
      --bg: #f5f7fa;
      --panel: #ffffff;
      --text: #18202a;
      --muted: #667386;
      --line: #d9e1ea;
      --green: #198754;
      --red: #bd3f3f;
      --blue: #1f6ed4;
      --yellow: #b77900;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, Segoe UI, Arial, sans-serif;
    }

    header {
      background: var(--panel);
      border-bottom: 1px solid var(--line);
      padding: 18px 24px;
    }

    h1 {
      margin: 0;
      font-size: 22px;
      font-weight: 700;
      letter-spacing: 0;
    }

    main {
      width: min(1180px, calc(100% - 32px));
      margin: 20px auto 36px;
    }

    .toolbar {
      display: grid;
      grid-template-columns: 1fr auto auto;
      gap: 12px;
      align-items: center;
      margin-bottom: 18px;
    }

    .meta {
      color: var(--muted);
      font-size: 14px;
      line-height: 1.5;
    }

    select,
    button {
      height: 38px;
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--text);
      border-radius: 6px;
      padding: 0 12px;
      font: inherit;
    }

    button {
      min-width: 110px;
      background: var(--blue);
      border-color: var(--blue);
      color: #fff;
      cursor: pointer;
    }

    .status {
      margin-bottom: 16px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 6px;
      color: var(--muted);
      font-size: 14px;
    }

    .status.error {
      color: var(--red);
      border-color: #efb2b2;
      background: #fff7f7;
    }

    .summary {
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }

    .metric {
      min-height: 92px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }

    .metric span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .06em;
    }

    .metric strong {
      display: block;
      margin-top: 10px;
      font-size: 26px;
      letter-spacing: 0;
      overflow-wrap: anywhere;
    }

    .charts {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-bottom: 16px;
    }

    .chart-box,
    .table-wrap {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }

    .chart-box h2,
    .table-wrap h2 {
      margin: 0 0 12px;
      font-size: 16px;
      letter-spacing: 0;
    }

    canvas {
      width: 100%;
      height: 320px;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }

    th,
    td {
      border-bottom: 1px solid var(--line);
      padding: 9px 8px;
      text-align: right;
      white-space: nowrap;
    }

    th:first-child,
    td:first-child {
      text-align: left;
    }

    th {
      color: var(--muted);
      font-weight: 600;
    }

    @media (max-width: 900px) {
      .toolbar,
      .charts {
        grid-template-columns: 1fr;
      }

      .summary {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }

      .table-wrap {
        overflow-x: auto;
      }
    }
  </style>
</head>
<body>
  <header>
    <h1>CarePlus Sprint 03 - Dashboard FIWARE</h1>
  </header>

  <main>
    <section class="toolbar">
      <div class="meta">
        Entidade: <strong>{{ entity_id }}</strong> | Tipo: <strong>{{ entity_type }}</strong><br>
        FIWARE: <strong>{{ fiware_host }}</strong> | STH: <strong>{{ sth_comet_url }}</strong> | API local: <strong>:{{ dashboard_port }}</strong>
      </div>
      <select id="lastN">
        <option value="20">Ultimos 20</option>
        <option value="50">Ultimos 50</option>
        <option value="100" selected>Ultimos 100</option>
        <option value="200">Ultimos 200</option>
      </select>
      <button id="refreshBtn" type="button">Atualizar</button>
    </section>

    <div id="status" class="status">Carregando historico do STH-Comet...</div>

    <section class="summary">
      <div class="metric"><span>Passos</span><strong id="steps">--</strong></div>
      <div class="metric"><span>Distancia</span><strong id="distanceKm">--</strong></div>
      <div class="metric"><span>Pontos</span><strong id="points">--</strong></div>
      <div class="metric"><span>Status</span><strong id="validationStatus">--</strong></div>
      <div class="metric"><span>Ultimo registro</span><strong id="lastRecvTime">--</strong></div>
    </section>

    <section class="charts">
      <div class="chart-box">
        <h2>Passos ao longo do tempo</h2>
        <canvas id="stepsChart"></canvas>
      </div>
      <div class="chart-box">
        <h2>Distancia estimada</h2>
        <canvas id="distanceChart"></canvas>
      </div>
    </section>

    <section class="table-wrap">
      <h2>Historico recebido do STH-Comet</h2>
      <table>
        <thead>
          <tr>
            <th>Horario</th>
            <th>steps</th>
            <th>m</th>
            <th>km</th>
            <th>points</th>
            <th>status</th>
            <th>totem</th>
            <th>mission</th>
            <th>user</th>
          </tr>
        </thead>
        <tbody id="historyRows"></tbody>
      </table>
    </section>
  </main>

  <script>
    let stepsChart;
    let distanceChart;

    function valueOf(row, key) {
      return row[key] ?? null;
    }

    function compactTime(value) {
      if (!value) return "--";
      const date = new Date(value);
      return Number.isNaN(date.getTime()) ? value : date.toLocaleString("pt-BR");
    }

    function chartLabels(history) {
      return history.map(row => {
        const date = new Date(row.recvTime);
        return Number.isNaN(date.getTime()) ? row.recvTime : date.toLocaleTimeString("pt-BR");
      });
    }

    function setMetric(id, value, suffix = "") {
      document.getElementById(id).textContent =
        value === undefined || value === null || value === "" ? "--" : `${value}${suffix}`;
    }

    function renderMetrics(latest) {
      setMetric("steps", latest.steps);
      setMetric("distanceKm", latest.distanceKm, latest.distanceKm === undefined ? "" : " km");
      setMetric("points", latest.points);
      setMetric("validationStatus", latest.validationStatus);
      setMetric("lastRecvTime", compactTime(latest.lastRecvTime));
    }

    function renderCharts(history) {
      const labels = chartLabels(history);
      const options = {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        scales: { y: { beginAtZero: true } }
      };

      if (stepsChart) stepsChart.destroy();
      if (distanceChart) distanceChart.destroy();

      stepsChart = new Chart(document.getElementById("stepsChart"), {
        type: "line",
        data: {
          labels,
          datasets: [
            {
              label: "steps",
              data: history.map(row => valueOf(row, "steps")),
              borderColor: "#1f6ed4",
              backgroundColor: "rgba(31, 110, 212, .12)",
              tension: .25
            }
          ]
        },
        options
      });

      distanceChart = new Chart(document.getElementById("distanceChart"), {
        type: "line",
        data: {
          labels,
          datasets: [
            {
              label: "distanceMeters",
              data: history.map(row => valueOf(row, "distanceMeters")),
              borderColor: "#198754",
              backgroundColor: "rgba(25, 135, 84, .12)",
              tension: .25
            }
          ]
        },
        options
      });
    }

    function renderRows(history) {
      const rows = history.slice(-30).reverse().map(row => `
        <tr>
          <td>${compactTime(row.recvTime)}</td>
          <td>${row.steps ?? "--"}</td>
          <td>${row.distanceMeters ?? "--"}</td>
          <td>${row.distanceKm ?? "--"}</td>
          <td>${row.points ?? "--"}</td>
          <td>${row.validationStatus ?? "--"}</td>
          <td>${row.totemId ?? "--"}</td>
          <td>${row.missionId ?? "--"}</td>
          <td>${row.userId ?? "--"}</td>
        </tr>
      `).join("");

      document.getElementById("historyRows").innerHTML =
        rows || "<tr><td colspan='9'>Sem historico ainda. Atualize a entidade FIWARE pelo Postman.</td></tr>";
    }

    async function loadDashboard() {
      const status = document.getElementById("status");
      const lastN = document.getElementById("lastN").value;
      status.className = "status";
      status.textContent = "Carregando historico do STH-Comet...";

      try {
        const response = await fetch(`/api/history?lastN=${lastN}`);
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Falha ao carregar historico");

        const history = data.history || [];
        renderMetrics(data.latest || {});
        renderCharts(history);
        renderRows(history);

        const partial = data.ok ? "" : " Alguns atributos falharam.";
        status.textContent = `Atualizado. Registros: ${history.length}.${partial}`;
        status.className = data.ok ? "status" : "status error";
      } catch (error) {
        status.textContent = `Erro ao consultar STH-Comet: ${error.message}`;
        status.className = "status error";
      }
    }

    document.getElementById("refreshBtn").addEventListener("click", loadDashboard);
    document.getElementById("lastN").addEventListener("change", loadDashboard);
    loadDashboard();
    setInterval(loadDashboard, 30000);
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=DASHBOARD_PORT)
