# GenAI Project 1

This repository contains two LangChain notebooks and a Streamlit research app.

- `1_document_loader/`: URL and CSV document-loading examples. The URL example
  uses a local sample when the remote article is unavailable.
- `2_text_splitter/`: manual and LangChain text-splitting examples.
- `real-estate-tool/`: a question-answering app for HTML pages. It can process
  articles on any topic, despite its name.

## Run locally

Use Python 3.12 from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Select `.venv/bin/python` as the notebook kernel in VS Code. For the app, copy
`real-estate-tool/.env.example` to `real-estate-tool/.env`, add your Groq API key,
then run:

```bash
python -m streamlit run real-estate-tool/main.py
```

See [the app README](real-estate-tool/README.md) for more detail. The `.env`
file, virtual environment, and generated vector database are ignored by Git.
