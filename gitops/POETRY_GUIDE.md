# Poetry Installation Guide

## 📦 Dependency Groups

Este proyecto usa Poetry con grupos de dependencias separados:

- **main**: Dependencias de producción (kubernetes, pyyaml, requests, etc.)
- **test**: Dependencias para testing (pytest, hypothesis, etc.)
- **dev**: Herramientas de desarrollo (black, flake8, mypy, etc.)
- **docs**: Herramientas de documentación (mkdocs, mkdocs-material)

## 🚀 Instalación por Caso de Uso

### Para Desarrollo Local (TODO)

```bash
poetry install
```

Instala todas las dependencias (main + test + dev + docs)

### Para CI/CD (Solo Tests)

```bash
poetry install --only main,test
```

Instala solo lo necesario para ejecutar tests

### Para Producción (Mínimo)

```bash
poetry install --only main
```

Instala solo las dependencias de producción

### Para Generar Documentación

```bash
poetry install --only main,docs
```

Instala lo necesario para construir la documentación

## 📊 Comparación de Tamaños

| Instalación        | Paquetes | Uso Recomendado        |
| ------------------ | -------- | ---------------------- |
| `--only main`      | ~10      | Producción, containers |
| `--only main,test` | ~20      | CI/CD pipelines        |
| `install` (todo)   | ~64      | Desarrollo local       |

## 🎯 Mejores Prácticas

### ✅ HACER:

- Usar `--only main` en Dockerfiles de producción
- Usar `--only main,test` en CI/CD
- Instalar todo solo en desarrollo local

### ❌ NO HACER:

- Instalar dependencias de dev en producción
- Instalar mkdocs en containers de runtime
- Usar `poetry install` sin flags en CI/CD

## 🐳 Ejemplo Dockerfile

```dockerfile
# Dockerfile para producción
FROM python:3.9-slim

WORKDIR /app

# Instalar Poetry
RUN pip install poetry

# Copiar archivos de dependencias
COPY pyproject.toml poetry.lock ./

# Instalar SOLO dependencias de producción
RUN poetry install --only main --no-root

# Copiar código
COPY . .

CMD ["poetry", "run", "python", "scripts/setup.py"]
```

## 🔄 Actualizar Dependencias

```bash
# Actualizar todas las dependencias
poetry update

# Actualizar solo un grupo
poetry update --only main

# Ver dependencias obsoletas
poetry show --outdated
```

## 📝 Notas

- El `poetry.lock` debe estar en el repositorio
- Usar `poetry lock --no-update` para regenerar lock sin actualizar versiones
- Las dependencias de test incluyen hypothesis para property-based testing
