"""Frozen Qwen3.5-9B rollout service. Starts inference only when explicitly executed."""

import argparse
import json
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .contracts import fingerprint, reject_private_fields
from .train_adapter import digest, policy_prompt_ids


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--adapter", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--device", type=int, required=True)
    parser.add_argument(
        "--arm", choices=["simjecture_raw9b", "simjecture_sft9b", "simjecture_sftrl9b"], required=True
    )
    parser.add_argument("--port", type=int, default=19190)
    parser.add_argument("--receipts", type=Path)
    args = parser.parse_args()
    if (args.arm == "simjecture_raw9b") != (args.adapter is None):
        raise ValueError("Raw 9B uses no adapter; SFT and SFT/RL arms require their pinned adapter")
    cfg = json.loads(args.config.read_bytes())
    manifest = json.loads((args.base / "verified-manifest.json").read_bytes())
    if manifest["repository"] != "Qwen/Qwen3.5-9B" or manifest["revision"] != cfg["base_revision"]:
        raise ValueError("Unexpected base model")
    import torch
    import torch_npu  # noqa: F401
    from peft import PeftModel
    from transformers import AutoModelForImageTextToText, AutoTokenizer

    torch.npu.set_device(args.device)
    device = torch.device(f"npu:{args.device}")
    model = AutoModelForImageTextToText.from_pretrained(
        args.base, torch_dtype=torch.bfloat16, local_files_only=True, attn_implementation="sdpa"
    )
    if args.adapter:
        model = PeftModel.from_pretrained(model, args.adapter, is_trainable=False)
        policy_sha = digest(args.adapter / "adapter_model.safetensors")
    else:
        policy_sha = fingerprint(manifest)
    model.to(device).eval()
    tokenizer = AutoTokenizer.from_pretrained(args.base, local_files_only=True)
    lock = threading.Lock()
    started_at = time.time()
    cache = {}
    from jsonschema import Draft202012Validator

    from .storage import read_json, write_json

    schema = json.loads((Path(__file__).resolve().parents[1] / "schemas/advice.schema.json").read_bytes())
    validator = Draft202012Validator(schema)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            result = dict(
                ready=True,
                arm=args.arm,
                policy_sha256=policy_sha,
                device=args.device,
                started_at=started_at,
                model="Qwen/Qwen3.5-9B",
            )
            payload = json.dumps(result).encode()
            self.send_response(200 if self.path == "/health" else 404)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self):
            try:
                if self.path != "/advice":
                    raise ValueError("Unknown endpoint")
                request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if request["expected_arm"] != args.arm:
                    raise ValueError("Requested arm differs from the pinned model service")
                state = request["observation"]
                reject_private_fields(state)
                identifier = request.get("request_id") or uuid.uuid4().hex
                if not identifier.isalnum() or len(identifier) > 128:
                    raise ValueError("Request id must be an opaque alphanumeric token")
                request_hash = fingerprint(request)
                receipt_path = args.receipts / (identifier + ".json") if args.receipts else None
                prompt = policy_prompt_ids(tokenizer, state)
                if len(prompt) > cfg["input_tokens_initial"]:
                    raise ValueError(
                        "State exceeds context capacity; request a rebuilt evidence-linked state"
                    )
                with lock, torch.no_grad():
                    prior = read_json(receipt_path) if receipt_path else cache.get(identifier)
                    if prior:
                        if prior["request_sha256"] != request_hash:
                            raise ValueError("Request id was retried with different scientific inputs")
                        self.reply(200, prior["reply"])
                        return
                    remaining = state["observed_at"] + state["remaining_wall_seconds"] - time.time()
                    if remaining <= 0:
                        raise ValueError("Study deadline expired before inference admission")
                    torch.manual_seed(request["seed"])
                    inputs = torch.tensor([prompt], device=device)
                    inference_started = time.time()
                    generated = model.generate(
                        input_ids=inputs,
                        attention_mask=torch.ones_like(inputs),
                        do_sample=True,
                        temperature=cfg["rloo"]["sampling_temperature"],
                        top_k=0,
                        top_p=1.0,
                        repetition_penalty=1.0,
                        max_new_tokens=cfg["output_tokens_initial"],
                        max_time=remaining,
                        use_cache=True,
                        return_dict_in_generate=True,
                        output_scores=True,
                    )
                    response = generated.sequences[0, len(prompt) :].tolist()
                    probability = sum(
                        torch.log_softmax(scores.float(), dim=-1)[0, token]
                        for scores, token in zip(generated.scores, response)
                    )
                    token_probabilities = [
                        float(torch.log_softmax(scores.float(), dim=-1)[0, token])
                        for scores, token in zip(generated.scores, response)
                    ]
                    raw = tokenizer.decode(response, skip_special_tokens=True)
                    try:
                        advice = json.loads(raw)
                        reject_private_fields(advice)
                        validator.validate(advice)
                        validation_error = None
                    except Exception as error:
                        advice = None
                        validation_error = "Invalid structured advice: " + str(error)[:800]
                    result = dict(
                        advice=advice,
                        raw_output=raw,
                        input_ids=prompt,
                        response_ids=response,
                        behavior_logprob=float(probability),
                        behavior_token_logprobs=token_probabilities,
                        policy_sha256=policy_sha,
                        observation_sha256=fingerprint(state),
                        temperature=cfg["rloo"]["sampling_temperature"],
                        validation_error=validation_error,
                        request_id=identifier,
                        inference_wall_seconds=time.time() - inference_started,
                    )
                    persisted = dict(request_sha256=request_hash, reply=result)
                    if receipt_path:
                        write_json(receipt_path, persisted, immutable=True)
                    else:
                        cache[identifier] = persisted
                status = 200
            except (ValueError, KeyError, TypeError) as error:
                result = dict(error=str(error))
                status = 400
            self.reply(status, result)

        def reply(self, status, result):
            payload = json.dumps(result, allow_nan=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
