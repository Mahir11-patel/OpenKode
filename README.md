# Separate DistilGPT2 fine-tuning experiment

This folder is separate from the existing KODE.MINI Python assistant. The Open-Kode website console issues keys for KODE.MINI, not this experimental model. The scripts and key database here are only for the optional DistilGPT2 fine-tuning prototype.

This trains a small text-generation model from a licensed pretrained checkpoint and a bounded sample of the local Open-Kode Q&A knowledge base. It does not train a ChatGPT-scale foundation model from scratch. The default base is Hugging Face DistilGPT2 (82 million parameters, Apache 2.0); expect short, basic English answers.

The source knowledge base at `D:\Codex\data\knowledge_base.json` is read locally and never uploaded by these scripts. It currently contains malformed JSON. The preparation script keeps only complete Q&A records before the first parse error and leaves the original file untouched. Training samples and model weights are ignored by Git and excluded from the public website.

## Prepare the sample

From `D:\Codex\openkode-site`:

```powershell
python -m pip install -r training/requirements.txt
python training/prepare_dataset.py
```

The default creates at most 350 shuffled records in `training/data/openkode_train.jsonl`. You can choose another local source with `--source` and increase the sample count with `--max-samples`.

## Fine-tune on this computer

```powershell
python training/train_local.py
```

The first run downloads the Apache-licensed base checkpoint into the normal Hugging Face cache. Training uses CPU, one example at a time, and an Adafactor optimizer to keep memory use lower. Output weights go to `training/output/openkode-distilgpt2`; the training script does not publish or host them.

This computer has 2 CPU cores, 3.9 GB RAM, and CPU-only PyTorch. The training script checks available RAM before importing PyTorch and stops unless at least 2 GB is free. At last check, only 0.36 GB was free, so the run was not started. Training is CPU-only and can be slow. Netlify hosts the website files, while this model needs a separate Python process to run inference.

## Start the local API and issue keys

After training completes, open a second PowerShell window in the site folder and run:

```powershell
python training/api_server.py
```

The server binds to `127.0.0.1:9000` by default. It provides `GET /health` and an OpenAI-compatible `POST /v1/chat/completions` endpoint. Create an owner key (permanent access) or an explicitly dated subscriber key:

```powershell
python training/manage_api_key.py create --email mahir31891@gmail.com --label "Owner"
python training/manage_api_key.py create --email member@example.com --label "Subscriber" --paid-until 2027-01-01
python training/manage_api_key.py revoke --id KEY_ID
```

The CLI prints each key once and stores only its SHA-256 hash in `runtime/model-api.sqlite3`. Keep the key private. Subscriber dates are manual because checkout has not been selected or connected. The API has per-key rate limiting, but it is a local prototype: it has no TLS, web self-service, subscription verification, multi-user hosting, or production security review. Do not expose this server directly to the public internet. Netlify can host the site, but this Python model needs a separate HTTPS-protected Python host for remote API access.

Example request from PowerShell:

```powershell
$headers = @{ Authorization = "Bearer YOUR_OPENKODE_KEY" }
$body = @{ model = "openkode-local-prototype"; messages = @(@{ role = "user"; content = "What can Open-Kode do?" }) } | ConvertTo-Json -Depth 6
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:9000/v1/chat/completions -Headers $headers -ContentType "application/json" -Body $body
```
