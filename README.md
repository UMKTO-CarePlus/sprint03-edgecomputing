# CarePlus Sprint 03 - Edge Computing

Repositório da entrega de Edge Computing da Sprint 03 do Challenge CarePlus.

A solução mantém o app/back-end CarePlus publicado no Render e usa FIWARE na VM do professor como camada oficial de IoT, histórico e dashboard.

## Estrutura

```text
iot/sprint03_hybrid_esp32/                 Firmware ESP32 hibrido FIWARE + Render
docs/sprint03-render-fiware.md             Arquitetura, operação e roteiro de teste
postman/CarePlus_Sprint03_Render_FIWARE.postman_collection.json
dashboard_colab/careplus_sprint03_fiware_dashboard.py
INTEGRANTES.TXT
```

## Fluxo

```text
ESP32 -> MQTT/Mosquitto -> IoT Agent -> Orion -> STH-Comet -> Dashboard
ESP32 -> FastAPI no Render quando a missão é validada
Frontend/App CarePlus -> FastAPI no Render
```

## Execução resumida

1. Subir a VM FIWARE do professor.
2. Importar a collection Postman.
3. Rodar os health checks de Orion, IoT Agent e STH-Comet.
4. Provisionar service/device `token001`.
5. Gravar o firmware em `iot/sprint03_hybrid_esp32/sprint03_hybrid_esp32.ino`.
6. Iniciar a coleta no app CarePlus/Render.
7. Validar a missão no ESP32.
8. Conferir entidade no Orion, histórico no STH-Comet e dashboard.

Detalhes completos em `docs/sprint03-render-fiware.md`.
