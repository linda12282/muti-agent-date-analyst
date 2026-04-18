"""Excel / CSV / TSV 等安全加载（不执行任意代码）。"""

from __future__ import annotations

import io
import json
from typing import Any, Dict, Optional, Tuple

import pandas as pd


def load_tabular(filename: str, raw: bytes) -> Tuple[pd.DataFrame, str]:
    name = (filename or "data").lower()
    bio = io.BytesIO(raw)
    if name.endswith(".csv"):
        df = pd.read_csv(bio)
        return df, "csv"
    if name.endswith(".tsv") or name.endswith(".txt"):
        df = pd.read_csv(bio, sep="\t")
        return df, "tsv"
    if name.endswith(".xlsx") or name.endswith(".xlsm"):
        df = pd.read_excel(bio, engine="openpyxl")
        return df, "xlsx"
    if name.endswith(".xls"):
        raise ValueError("旧版 .xls 请另存为 .xlsx 后再上传")
    if name.endswith(".jsonl") or name.endswith(".ndjson"):
        df = pd.read_json(bio, lines=True)
        return df, "jsonl"
    if name.endswith(".json"):
        j = json.loads(raw.decode("utf-8", errors="replace"))
        if isinstance(j, list):
            df = pd.json_normalize(j)
        elif isinstance(j, dict):
            df = pd.json_normalize([j])
        else:
            raise ValueError("不支持的 JSON 结构")
        return df, "json"
    # 默认按 csv 尝试
    try:
        df = pd.read_csv(io.BytesIO(raw))
        return df, "csv_guess"
    except Exception:
        raise ValueError("无法识别文件类型，请上传 csv / tsv / xlsx / jsonl / json 数组")


def df_profile(df: pd.DataFrame, max_rows: int = 8) -> Dict[str, Any]:
    desc = {}
    try:
        desc_obj = df.describe(include="all")
        desc = desc_obj.to_dict()
    except Exception:
        desc = {}
    nulls = df.isnull().sum().to_dict()
    dtypes = {c: str(t) for c, t in df.dtypes.items()}
    preview = df.head(max_rows).to_dict(orient="records")
    return {
        "n_rows": int(len(df)),
        "n_cols": int(len(df.columns)),
        "columns": list(df.columns),
        "dtypes": dtypes,
        "null_counts": {str(k): int(v) for k, v in nulls.items()},
        "describe": desc,
        "preview": preview,
    }
