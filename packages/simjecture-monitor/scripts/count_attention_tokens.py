"""CPU tokenizer subprocess for contract experiments; no model weights are loaded."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

from simjecture_monitor.model import SYSTEM
from transformers import AutoTokenizer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokenizer", type=Path, required=True)
    args = parser.parse_args()
    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, local_files_only=True)
    symbols = {symbol: tokenizer.encode(symbol, add_special_tokens=False) for symbol in "ABCDE"}
    marker = tokenizer.encode("<decision>", add_special_tokens=False)
    if len(marker) != 1 or any(len(ids) != 1 for ids in symbols.values()):
        raise ValueError("This route-only profile needs single-token symbols and marker")
    print(
        json.dumps(
            dict(
                tokenizer=str(args.tokenizer.resolve()),
                tokenizer_sha256=hashlib.sha256(
                    (args.tokenizer / "tokenizer.json").read_bytes()
                ).hexdigest(),
                template_sha256=hashlib.sha256(
                    (args.tokenizer / "chat_template.jinja").read_bytes()
                ).hexdigest(),
                system_sha256=hashlib.sha256(SYSTEM.encode()).hexdigest(),
                symbol_token_ids=symbols,
                marker_token_ids=marker,
            )
        ),
        flush=True,
    )
    for line in sys.stdin:
        text = json.loads(line)
        rendered = tokenizer.apply_chat_template(
            [
                dict(role="system", content=SYSTEM),
                dict(role="user", content=text),
                dict(role="assistant", content='{\n    "attention": "<decision>"\n}'),
            ],
            tokenize=False,
            add_generation_prompt=False,
            enable_thinking=False,
        )
        print(json.dumps(len(tokenizer.encode(rendered, add_special_tokens=False))), flush=True)


if __name__ == "__main__":
    main()
