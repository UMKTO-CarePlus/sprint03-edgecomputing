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
http://localhost:8666
```

Na VM FIWARE da entrega, o acesso publico esperado e:

```text
http://34.69.120.192:8666
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
STH_COMET_URL=http://34.69.120.192:8666
DASHBOARD_PORT=8666
FIWARE_SERVICE=openiot
FIWARE_SERVICE_PATH=/
ENTITY_ID=CarePlusMission:totem001
ENTITY_TYPE=CarePlusWalkingMission
```

Se o dashboard tambem estiver publicado na porta `8666`, ajuste `STH_COMET_URL` para o endereco interno do STH-Comet. Assim a porta publica `8666` fica com o dashboard e o STH-Comet continua sendo consultado pela rede interna.

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
curl http://localhost:8666/
curl http://localhost:8666/api/health
curl "http://localhost:8666/api/history?lastN=5"
```

## Liberar porta 8666 na GCP

Crie uma regra de firewall de entrada:

```text
Nome: careplus-dashboard-8666
Direcao: Entrada
Acao: Permitir
Alvos: VM FIWARE ou tag de rede da VM
Origem IPv4: 0.0.0.0/0
Protocolos e portas: tcp:8666
Prioridade: 1000
```

Com `gcloud`, o comando equivalente e:

```bash
gcloud compute firewall-rules create careplus-dashboard-8666 \
  --direction=INGRESS \
  --priority=1000 \
  --network=default \
  --action=ALLOW \
  --rules=tcp:8666 \
  --source-ranges=0.0.0.0/0
```

Depois acesse:

```text
http://34.69.120.192:8666
```
