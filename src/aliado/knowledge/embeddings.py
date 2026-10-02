"""Encoder local carregado sob demanda; não baixa arquivos implicitamente."""

from __future__ import annotations

import os
from hashlib import sha256
from pathlib import Path

MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
MODEL_FILE = "onnx/model_quint8_avx2.onnx"
ARTIFACT_HASHES = {
    "tokenizer.json": "2c3387be76557bd40970cec13153b3bbf80407865484b209e655e5e4729076b8",
    MODEL_FILE: "98a01d88b7de996cdea58c32ca71208c09968d143798814b2ea09d3439dc334f",
}
# Textos por chamada ao modelo. O modelo quantizado é sensível ao preenchimento do lote: quem codifica
# em fatias (a indexação, lote 27) usa múltiplos deste número para obter os mesmos vetores.
ENCODE_BATCH = 16


class LocalEncoder:
    fingerprint = f"{MODEL}@{REVISION}:onnx-quint8:mean-normalized:chunks110-overlap20-v1"

    def __init__(self, directory: str | Path | None = None):
        self.directory = Path(directory or os.getenv("AL_IADO_EMBEDDINGS_DIR", "data/models/minilm"))
        self._tokenizer = None
        self._session = None

    def _artifact(self, name):
        path = self.directory / name
        if not path.is_file():
            raise ValueError("Modelo local ausente. Execute biblioteca preparar-modelo.")
        with path.open("rb") as handle:
            digest = sha256()
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != ARTIFACT_HASHES[name]:
            raise ValueError("Artefato do encoder diverge da revisão fixa; prepare o modelo novamente.")
        return path

    def _load_tokenizer(self):
        if self._tokenizer is None:
            from tokenizers import Tokenizer

            path = self._artifact("tokenizer.json")
            self._tokenizer = Tokenizer.from_file(str(path))
            self._tokenizer.no_truncation()
            self._tokenizer.no_padding()
        return self._tokenizer

    def split(self, text: str) -> list[str]:
        offsets = self._load_tokenizer().encode(text, add_special_tokens=False).offsets
        pieces = []
        for start in range(0, len(offsets), 90):
            end = min(start + 110, len(offsets))
            piece = text[offsets[start][0]:offsets[end - 1][1]].strip()
            if piece:
                pieces.append(piece)
            if end == len(offsets):
                break
        return pieces

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        import numpy as np
        import onnxruntime as ort

        tokenizer = self._load_tokenizer()
        if self._session is None:
            path = self._artifact(MODEL_FILE)
            options = ort.SessionOptions()
            options.intra_op_num_threads = 1
            self._session = ort.InferenceSession(str(path), options, providers=["CPUExecutionProvider"])
        outputs = []
        for start in range(0, len(texts), ENCODE_BATCH):
            encoded = tokenizer.encode_batch(texts[start:start + ENCODE_BATCH])
            if any(len(item.ids) > 128 for item in encoded):
                raise ValueError("Trecho ou consulta excede 128 tokens; divida o texto.")
            width = max(len(item.ids) for item in encoded)
            ids = np.zeros((len(encoded), width), dtype=np.int64)
            masks = np.zeros_like(ids)
            types = np.zeros_like(ids)
            for i, item in enumerate(encoded):
                n = len(item.ids)
                ids[i, :n] = item.ids
                masks[i, :n] = item.attention_mask
                types[i, :n] = item.type_ids
            available = {"input_ids": ids, "attention_mask": masks, "token_type_ids": types}
            inputs = {item.name: available[item.name] for item in self._session.get_inputs()}
            tokens = self._session.run(None, inputs)[0]
            mask = masks[..., None].astype(np.float32)
            pooled = (tokens * mask).sum(axis=1) / np.clip(mask.sum(axis=1), 1, None)
            pooled /= np.clip(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12, None)
            outputs.extend(pooled.tolist())
        return outputs


def prepare_model(directory: str | Path | None = None) -> dict:
    """Download explícito de dois artefatos da revisão fixa; não importa documentos."""
    from huggingface_hub import hf_hub_download

    target = LocalEncoder(directory).directory
    for name in ("tokenizer.json", MODEL_FILE):
        hf_hub_download(MODEL, name, revision=REVISION, local_dir=str(target))
        LocalEncoder(target)._artifact(name)
    return {"model": MODEL, "revision": REVISION, "directory": str(target.resolve())}
