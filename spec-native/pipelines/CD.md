# CD.md

Entrega continua de WebSpider.

## Alcance

WebSpider es una herramienta local de desarrollo y no tiene despliegue de
producción. La entrega actual consiste en ejecutar pruebas y publicar cambios
del repositorio; no se deben documentar ambientes ficticios.

## Plataforma y proceso

- **Plataforma:** GitHub Actions para gates de integración.
- **Configuración:** `.github/workflows/ci.yml` cuando se habilite el pipeline.
- **Destino:** instalación local desde el repositorio o paquete Python.
- **Deploy automático:** no aplica.

## Release local

1. Ejecutar lint, type check y tests.
2. Revisar los criterios de la iniciativa y su trazabilidad.
3. Crear commit Conventional Commit y revisar el diff.
4. Publicar el cambio mediante el flujo normal del repositorio.

## Gates

| De | A | Gates requeridos |
| --- | --- | --- |
| rama de trabajo | `main` | ruff, mypy, pytest y revisión de cambios |
| `main` | instalación local | paquete instalable y smoke test MCP |

## Variables y secretos

Las credenciales LLM y de `ether-websearch` se suministran por variables de
entorno o almacenamiento seguro local. No se guardan valores en
SpecNative, checkpoints ni reportes.

## Rollback

Para una regresión local, volver al commit estable anterior y reconstruir el
entorno virtual. Los checkpoints de misiones se conservan fuera del control de
versiones y deben revisarse antes de reutilizarse.
