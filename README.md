# CarePlus Sprint 03 - Edge Computing

Repositorio da entrega de Edge Computing da Sprint 03 do Challenge CarePlus.

A solucao usa o app CarePlus no celular para contar passos e validar a missao por NFC. O ESP32 representa o totem fisico, exibindo feedback com LED verde, LED vermelho e buzzer. O FIWARE/Orion/STH-Comet guarda o historico usado pelo dashboard web.

## Estrutura

```text
iot/sprint03_hybrid_esp32/                 Firmware ESP32 simples para LED/buzzer
iot/sprint03_hybrid_esp32/diagram.json     Circuito Wokwi com 2 LEDs e buzzer
postman/CarePlus_Sprint03_Render_FIWARE.postman_collection.json
dashboard_web/app.py                       Dashboard web Flask na porta 5000
dashboard_web/careplus-dashboard.service   Modelo de servico Linux
docs/sprint03-render-fiware.md             Arquitetura, operacao e roteiro de teste
INTEGRANTES.TXT
```

## Fluxo

```text
Celular/App CarePlus -> conta passos -> le tag NFC -> FastAPI no Render
FastAPI no Render -> status do totem
ESP32/Wokwi -> GET /iot/totem-status/totem001 -> LED verde/vermelho + buzzer
Postman -> Orion -> STH-Comet -> Dashboard web Flask
```

## Execucao resumida

1. Subir a VM FIWARE do professor.
2. Importar a collection Postman.
3. Rodar os health checks de Render, Orion e STH-Comet.
4. No Postman, executar o fluxo do app: listar totens, iniciar missao, sincronizar passos e validar NFC.
5. No Postman, criar/atualizar a entidade `CarePlusMission:totem001` para alimentar o STH-Comet.
6. Importar/simular no Wokwi a pasta `iot/sprint03_hybrid_esp32/`.
7. Usar os requests de feedback do Postman para testar `validating`, `success`, `error` e `idle` no ESP32.
8. Rodar `python dashboard_web/app.py` e acessar `http://localhost:5000`.
9. Conferir passos, distancia estimada, pontos e status no dashboard.

Detalhes completos em `docs/sprint03-render-fiware.md`.
