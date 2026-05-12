# CarePlus Sprint 03 - Dashboard FIWARE
# Cole este codigo em uma celula do Google Colab ou rode localmente com Python.

import requests
import pandas as pd
import matplotlib.pyplot as plt

FIWARE_URL = "34.69.120.192"
SERVICE = "openiot"
SERVICE_PATH = "/"
ENTITY_ID = "CarePlusToken:token001"
ENTITY_TYPE = "CarePlusToken"

HEADERS = {
    "fiware-service": SERVICE,
    "fiware-servicepath": SERVICE_PATH,
}


def get_json(url):
    response = requests.get(url, headers=HEADERS, timeout=20)
    print(response.status_code, url)
    response.raise_for_status()
    return response.json()


def get_orion_entity():
    url = f"http://{FIWARE_URL}:1026/v2/entities/{ENTITY_ID}?options=keyValues"
    return get_json(url)


def get_sth_attribute(attribute, last_n=100):
    url = (
        f"http://{FIWARE_URL}:8666/STH/v1/contextEntities/type/{ENTITY_TYPE}"
        f"/id/{ENTITY_ID}/attributes/{attribute}?lastN={last_n}"
    )
    data = get_json(url)
    responses = data.get("contextResponses", [])
    if not responses:
        return pd.DataFrame()

    attributes = responses[0].get("contextElement", {}).get("attributes", [])
    if not attributes:
        return pd.DataFrame()

    rows = []
    for item in attributes[0].get("values", []):
        rows.append(
            {
                "recvTime": item.get("recvTime") or item.get("recvTimeTs"),
                attribute: pd.to_numeric(item.get("attrValue"), errors="ignore"),
            }
        )
    return pd.DataFrame(rows)


print("Estado atual no Orion")
entity = get_orion_entity()
display(pd.DataFrame([entity]).T.rename(columns={0: "valor"}))

tracked_attributes = [
    "steps",
    "pendingSteps",
    "tokenValue",
    "totalPoints",
    "batteryLevel",
    "rssi",
    "accelX",
    "accelY",
    "accelZ",
]

frames = []
for attr in tracked_attributes:
    try:
        frame = get_sth_attribute(attr)
        if not frame.empty:
            frames.append(frame)
    except Exception as exc:
        print(f"Nao foi possivel ler {attr}: {exc}")

if not frames:
    print("Sem historico ainda. Crie a subscription no Postman e rode o ESP32 por alguns minutos.")
else:
    history = frames[0]
    for frame in frames[1:]:
        history = pd.merge(history, frame, on="recvTime", how="outer")

    history["recvTime"] = pd.to_datetime(history["recvTime"], errors="coerce")
    history = history.sort_values("recvTime").reset_index(drop=True)
    display(history.tail(20))

    main_cols = [col for col in ["steps", "pendingSteps", "totalPoints", "batteryLevel"] if col in history]
    if main_cols:
        history.plot(x="recvTime", y=main_cols, figsize=(12, 5), marker="o")
        plt.title("CarePlus Sprint 03 - passos, pontos e bateria")
        plt.xlabel("Horario")
        plt.ylabel("Valor")
        plt.grid(True)
        plt.show()

    accel_cols = [col for col in ["accelX", "accelY", "accelZ"] if col in history]
    if accel_cols:
        history.plot(x="recvTime", y=accel_cols, figsize=(12, 5), marker=".")
        plt.title("CarePlus Sprint 03 - acelerometro MPU6050")
        plt.xlabel("Horario")
        plt.ylabel("m/s2")
        plt.grid(True)
        plt.show()
