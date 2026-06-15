# CarePlus Sprint 03 - Dashboard Web FIWARE

Dashboard web em Python/Flask para apresentar passos, distancia estimada, pontos e validacoes historicas. O dashboard usa a porta `8080` e consulta o STH-Comet na porta `8666`.

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
http://localhost:8080
```

Na VM FIWARE da entrega, o acesso publico esperado e:

```text
http://34.69.120.192:8080
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
FIWARE_HOST=34.69.120.192
STH_COMET_URL=http://127.0.0.1:8666
DASHBOARD_PORT=8080
FIWARE_SERVICE=openiot
FIWARE_SERVICE_PATH=/
ENTITY_ID=CarePlusMission:totem001
ENTITY_TYPE=CarePlusWalkingMission
```

Na VM, o STH-Comet permanece em `127.0.0.1:8666`. O dashboard e publicado separadamente em `0.0.0.0:8080`, evitando conflito entre os dois servicos.

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

Teste dentro da VM:

```bash
curl http://localhost:8080/
curl http://localhost:8080/api/health
curl "http://localhost:8080/api/history?lastN=5"
```

## Liberar porta 8080 na GCP

Crie uma regra de firewall de entrada:

```text
Nome: careplus-dashboard-8080
Direcao: Entrada
Acao: Permitir
Alvos: VM FIWARE ou tag de rede da VM
Origem IPv4: 0.0.0.0/0
Protocolos e portas: tcp:8080
Prioridade: 1000
```

Com `gcloud`, o comando equivalente e:

```bash
gcloud compute firewall-rules create careplus-dashboard-8080 \
  --direction=INGRESS \
  --priority=1000 \
  --network=default \
  --action=ALLOW \
  --rules=tcp:8080 \
  --source-ranges=0.0.0.0/0
```

Depois acesse:

```text
http://34.69.120.192:8080
```
