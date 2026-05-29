# Atenea - Asistente virtual

Atenea es un asistente virtual de escritorio para Windows construido en Python.
Incluye interfaz grafica, entrada por microfono, salida por voz, memoria local,
acciones del sistema, automatizacion controlada e integracion con OpenAI y Gemini.

## Lenguajes y tecnologias recomendadas

- Python: logica principal del asistente, microfono, voz y comandos.
- Markdown: documentacion del proyecto.
- JSON o YAML: configuracion futura si el asistente crece.

## Instalacion

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Si `PyAudio` falla al instalar en Windows, prueba:

```powershell
pip install pipwin
pipwin install pyaudio
pip install -r requirements.txt
```

## IA con OpenAI y Gemini

El asistente puede usar OpenAI y Gemini para interpretar peticiones que no
coinciden con comandos predeterminados. La IA no ejecuta comandos directamente:
solo devuelve una intencion estructurada y el codigo local decide si es seguro
ejecutarla.

Configura tus API keys en PowerShell:

```powershell
$env:OPENAI_API_KEY="tu_api_key"
$env:GEMINI_API_KEY="tu_api_key"
```

Opcionalmente puedes cambiar modelos y orden de proveedores:

```powershell
$env:OPENAI_MODEL="gpt-5.2"
$env:GEMINI_MODEL="gemini-3.1-flash-lite"
$env:GEMINI_FALLBACK_MODELS="gemini-2.5-flash,gemini-3-flash-preview,gemini-2.0-flash"
$env:AI_PROVIDERS="openai,gemini"
```

Si OpenAI falla por cuota o error, el asistente intenta con Gemini. Puedes
cambiar el orden con:

```powershell
$env:AI_PROVIDERS="gemini,openai"
```

Despues ejecuta:

```powershell
.\.venv\Scripts\python.exe python.py
```

## Ejecutar

```powershell
.\.venv\Scripts\python.exe python.py
```

Para ejecutarlo como aplicacion sin consola visible en Windows, abre:

```text
start_atenea.bat
```

Tambien puedes abrir directamente `atenea_background.pyw`.

Modo segundo plano:

- Si cierras la ventana con la X, Atenea se oculta pero sigue ejecutandose.
- Di `hola`, `Atenea` o `hola Atenea` para activarla.
- Cuando responda `Que necesitas?`, di tu peticion.
- Di `mostrar ventana` para volver a ver la interfaz.
- Di `cerrar asistente` o `apagar asistente` para terminar el proceso.

O, si PowerShell se confunde con las rutas:

```powershell
& ".\.venv\Scripts\python.exe" ".\python.py"
```

Al ejecutar se abre una ventana. Presiona el boton `Hablar`, di tu
peticion y el asistente respondera con texto y voz.

El flujo de decision actual prioriza IA:

```text
contexto activo -> IA contextual -> IA normal -> comandos contextuales -> comandos locales
```

## Comandos disponibles

- "hola"
- "hora"
- "fecha"
- "abre google"
- "abre youtube"
- "abre gmail"
- "abre github"
- "abre bloc de notas"
- "abre calculadora"
- "abre paint"
- "abre explorador"
- "abre excel"
- "abre spotify"
- "abre visual studio code"
- "abre carpeta documentos"
- "abre carpeta descargas"
- "busca inteligencia artificial"
- "salir", "terminar" o "adios"

Los comandos conocidos se ejecutan primero. Si la aplicacion no esta en la
lista fija, el asistente intenta buscarla entre los accesos directos instalados
de Windows.

## Estructura

- `python.py`: archivo de entrada.
- `src/main.py`: crea y conecta las partes del asistente.
- `src/ui/desktop_app.py`: ventana de escritorio con boton para escuchar.
- `src/assistant.py`: modo consola, conservado por si se necesita.
- `src/config.py`: configuracion general.
- `src/core/memory.py`: memoria local para reutilizar intenciones y ahorrar llamadas a IA.
- `src/speech/listener.py`: escucha el microfono.
- `src/speech/speaker.py`: convierte texto en voz.
- `src/core/commands.py`: interpreta las peticiones.
- `src/core/actions.py`: ejecuta acciones del sistema.

## Memoria local

El asistente guarda intenciones ya resueltas por IA en:

```text
.assistant_memory/memory.json
```

Si vuelves a pedir algo igual, usa la memoria antes de llamar a la API. Esto
reduce peticiones, latencia y costo. No se cachean respuestas dinamicas como
hora o fecha.

## Subir a GitHub

El proyecto puede subirse a GitHub. No subas llaves API ni archivos locales.
El `.gitignore` excluye:

```text
.venv/
__pycache__/
.assistant_memory/
.env
*.log
```

Las llaves deben configurarse como variables de entorno:

```powershell
setx OPENAI_API_KEY "tu_api_key"
setx GEMINI_API_KEY "tu_api_key"
```
