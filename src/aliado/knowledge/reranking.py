"""Segunda rede local para selecionar páginas; nunca baixa modelos durante uma pergunta."""

from __future__ import annotations

import math
import os
import threading
from hashlib import sha256
from pathlib import Path

MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
REVISION = "1427fd652930e4ba29e8149678df786c240d8825"
MODEL_FILE = "onnx/model_quint8_avx2.onnx"
ARTIFACT_HASHES = {
    "tokenizer.json": "62c24cdc13d4c9952d63718d6c9fa4c287974249e16b7ade6d5a85e7bbb75626",
    MODEL_FILE: "6c2513767fb63d008a4377bef7a7a3555433d9436342bb53e35a3a72ffc52d4b",
}
BATCH_SIZE = 8
MAX_TOKENS = 384


class LocalReranker:
    fingerprint = f"{MODEL}@{REVISION}:onnx-quint8:tokens{MAX_TOKENS}"

    def __init__(self, directory: str | Path | None = None):
        self.directory = Path(directory or os.getenv("AL_IADO_RERANKER_DIR", "data/models/reranker"))
        self._tokenizer = self._session = None
        self._lock = threading.Lock()

    def _artifact(self, name: str) -> Path:
        path = self.directory / name
        if not path.is_file():
            raise ValueError("Modelo de reordenação ausente. Execute biblioteca preparar-reordenador.")
        digest = sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != ARTIFACT_HASHES[name]:
            raise ValueError("Artefato do reordenador diverge da revisão fixa; prepare o modelo novamente.")
        return path

    def score(self, query: str, texts: list[str]) -> list[float]:
        if not texts:
            return []
        import numpy as np
        import onnxruntime as ort
        from tokenizers import Tokenizer

        # O tokenizer tem configuração mutável; carga e inferência são serializadas.
        with self._lock:
            if self._session is None:
                tokenizer_path, model_path = self._artifact("tokenizer.json"), self._artifact(MODEL_FILE)
                tokenizer = Tokenizer.from_file(str(tokenizer_path))
                tokenizer.enable_truncation(max_length=MAX_TOKENS)
                tokenizer.enable_padding(pad_id=1, pad_token="<pad>")
                options = ort.SessionOptions()
                options.intra_op_num_threads = 1
                options.inter_op_num_threads = 1
                session = ort.InferenceSession(str(model_path), options, providers=["CPUExecutionProvider"])
                self._tokenizer, self._session = tokenizer, session
            scores = []
            for start in range(0, len(texts), BATCH_SIZE):
                batch = self._tokenizer.encode_batch([(query[:4000], text[:6000])
                                                       for text in texts[start:start + BATCH_SIZE]])
                available = {
                    "input_ids": np.array([item.ids for item in batch], dtype=np.int64),
                    "attention_mask": np.array([item.attention_mask for item in batch], dtype=np.int64),
                    "token_type_ids": np.array([item.type_ids for item in batch], dtype=np.int64),
                }
                inputs = {item.name: available[item.name] for item in self._session.get_inputs()}
                scores.extend(self._session.run(None, inputs)[0].reshape(-1).tolist())
            if len(scores) != len(texts) or not all(math.isfinite(value) for value in scores):
                raise ValueError("Saída inválida do reordenador local.")
            return scores


def rank_pages(reranker, query: str, candidates: list[dict]) -> tuple[list[tuple], dict]:
    """Melhor escore de até dois trechos por página. Escores ordenam; não são probabilidades.

    O limite de 60 já é aplicado pela busca. A ordem original desempata e é preservada quando
    o modelo opcional está ausente ou falha. Nenhum documento novo é introduzido aqui.
    """
    pages, selected, counts = [], [], {}
    for item in candidates[:60]:
        key = (item["document_id"], item["page"] if item["page"] is not None else item["locator"])
        if key not in counts:
            pages.append(key)
        counts[key] = counts.get(key, 0) + 1
        if counts[key] <= 2:
            selected.append((key, item))
    if not selected or reranker is None:
        return pages, {"estado": "sem_candidatos" if not selected else "nao_configurada"}
    try:
        scores = reranker.score(query, [f"{item['title']} · {item['locator']}\n{item['text']}"
                                        for _, item in selected])
        if len(scores) != len(selected) or not all(math.isfinite(value) for value in scores):
            raise ValueError("Escores inválidos.")
    except Exception:
        # Esta etapa é opcional. Erros locais não derrubam a busca nem expõem caminhos na resposta.
        return pages, {"estado": "indisponivel", "aviso": "Reordenação local indisponível; usada a ordem da busca."}
    best = {}
    for (key, _), score in zip(selected, scores, strict=True):
        best[key] = max(best.get(key, -math.inf), score)
    return sorted(pages, key=lambda key: -best[key]), {
        "estado": "aplicada", "candidatos": len(selected), "paginas": len(pages),
        "modelo": getattr(reranker, "fingerprint", "local"),
    }


def prepare_model(directory: str | Path | None = None) -> dict:
    """Baixa somente os artefatos públicos fixados; não lê nem envia documentos."""
    from huggingface_hub import hf_hub_download

    reranker = LocalReranker(directory)
    for name in ARTIFACT_HASHES:
        hf_hub_download(MODEL, name, revision=REVISION, local_dir=str(reranker.directory))
        reranker._artifact(name)
    return {"model": MODEL, "revision": REVISION, "directory": str(reranker.directory.resolve())}
