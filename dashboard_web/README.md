# CarePlus Sprint 03 - Dashboard Web FIWARE

Dashboard web em Python/Flask para apresentar passos, distancia estimada, pontos e validacoes historicas consumidas da API STH-Comet na porta `8666`.

## Rodar localmente

```bash
cd dashboard_web
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Acesse:

```text
http://localhost:5000
```

## APIs disponiveis

```text
GET /api/health
GET /api/entity
GET /api/history?lastN=100
GET /api/history/steps?lastN=100
GET /api/history/distanceMeters?lastN=100
```

## Variaveis de ambiente

```text
FIWARE_HOST=35.198.7.130
FIWARE_SERVICE=openiot
FIWARE_SERVICE_PATH=/
ENTITY_ID=CarePlusMission:totem001
ENTITY_TYPE=CarePlusWalkingMission
```

## Instalar como servico Linux

Exemplo considerando deploy em `/opt/careplus-dashboard`:

```bash
sudo mkdir -p /opt/careplus-dashboard
sudo cp app.py requirements.txt careplus-dashboard.service /opt/careplus-dashboard/
cd /opt/careplus-dashboard
sudo python3 -m venv venv
sudo /opt/careplus-dashboard/venv/bin/pip install -r requirements.txt
sudo cp careplus-dashboard.service /etc/systemd/system/careplus-dashboard.service
sudo systemctl daemon-reload
sudo systemctl enable careplus-dashboard
sudo systemctl start careplus-dashboard
sudo systemctl status careplus-dashboard
```

Depois acesse:

```text
http://IP_DA_VM:5000
```
