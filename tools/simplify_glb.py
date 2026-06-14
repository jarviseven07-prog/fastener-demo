import argparse
import json
import struct
from pathlib import Path

import numpy as np


CT_FLOAT = 5126
CT_U16 = 5123
CT_U32 = 5125


def pad4(data: bytes, pad: bytes = b"\x00") -> bytes:
    return data + pad * ((4 - len(data) % 4) % 4)


def read_glb(path: Path):
    data = path.read_bytes()
    if data[:4] != b"glTF":
        raise ValueError(f"{path} is not a GLB")
    version, total = struct.unpack_from("<II", data, 4)
    if version != 2 or total != len(data):
        raise ValueError(f"{path} has unsupported GLB header")
    json_len, json_type = struct.unpack_from("<I4s", data, 12)
    if json_type != b"JSON":
        raise ValueError(f"{path} first chunk is not JSON")
    doc = json.loads(data[20 : 20 + json_len].decode("utf8").rstrip("\x00 \t\r\n"))
    bin_header = 20 + json_len
    bin_len, bin_type = struct.unpack_from("<I4s", data, bin_header)
    if bin_type != b"BIN\x00":
        raise ValueError(f"{path} second chunk is not BIN")
    blob = data[bin_header + 8 : bin_header + 8 + bin_len]
    return doc, blob


def accessor_array(doc, blob, accessor_index):
    acc = doc["accessors"][accessor_index]
    bv = doc["bufferViews"][acc["bufferView"]]
    offset = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    count = acc["count"]
    typ = acc["type"]
    ncomp = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[typ]
    ctype = acc["componentType"]
    dtype = {CT_FLOAT: np.float32, CT_U16: np.uint16, CT_U32: np.uint32}[ctype]
    stride = bv.get("byteStride")
    item = np.dtype(dtype).itemsize * ncomp
    if stride and stride != item:
        rows = np.empty((count, ncomp), dtype=dtype)
        for i in range(count):
            start = offset + i * stride
            rows[i] = np.frombuffer(blob, dtype=dtype, count=ncomp, offset=start)
        return rows[:, 0] if ncomp == 1 else rows
    arr = np.frombuffer(blob, dtype=dtype, count=count * ncomp, offset=offset)
    return arr.copy() if ncomp == 1 else arr.reshape((count, ncomp)).copy()


def dedupe_faces(tris):
    canon = np.sort(tris, axis=1)
    view = np.ascontiguousarray(canon).view([("a", canon.dtype), ("b", canon.dtype), ("c", canon.dtype)]).reshape(-1)
    _, keep = np.unique(view, return_index=True)
    keep.sort()
    return tris[keep]


def simplify_arrays(pos, normal, uv, indices, target_tris):
    tris0 = indices.reshape((-1, 3)).astype(np.int64)
    bmin = pos.min(axis=0)
    bmax = pos.max(axis=0)
    diag = float(np.linalg.norm(bmax - bmin))

    def run(cell):
        q = np.floor((pos - bmin) / cell).astype(np.int64)
        _, inv = np.unique(q, axis=0, return_inverse=True)
        tris = inv[tris0]
        good = (tris[:, 0] != tris[:, 1]) & (tris[:, 0] != tris[:, 2]) & (tris[:, 1] != tris[:, 2])
        tris = dedupe_faces(tris[good])
        return inv, tris

    lo = diag / 2000.0
    hi = diag / 50.0
    inv, tris = run(hi)
    while len(tris) > target_tris:
        hi *= 1.6
        inv, tris = run(hi)

    best = (abs(len(tris) - target_tris), inv, tris, hi)
    for _ in range(16):
        mid = (lo + hi) / 2
        inv_mid, tris_mid = run(mid)
        score = abs(len(tris_mid) - target_tris)
        if score < best[0] and len(tris_mid) <= target_tris * 1.08:
            best = (score, inv_mid, tris_mid, mid)
        if len(tris_mid) > target_tris:
            lo = mid
        else:
            hi = mid

    inv, tris, cell = best[1], best[2], best[3]
    used, remap = np.unique(tris.reshape(-1), return_inverse=True)
    new_tris = remap.reshape((-1, 3)).astype(np.uint32)
    nclusters = int(inv.max()) + 1

    sums = np.zeros((nclusters, 3), dtype=np.float64)
    nsums = np.zeros((nclusters, 3), dtype=np.float64)
    usums = np.zeros((nclusters, 2), dtype=np.float64)
    counts = np.bincount(inv, minlength=nclusters).astype(np.float64)
    np.add.at(sums, inv, pos)
    np.add.at(nsums, inv, normal)
    np.add.at(usums, inv, uv)

    new_pos = (sums[used] / counts[used, None]).astype(np.float32)
    new_norm = nsums[used]
    norm_len = np.linalg.norm(new_norm, axis=1)
    norm_len[norm_len == 0] = 1
    new_norm = (new_norm / norm_len[:, None]).astype(np.float32)
    new_uv = (usums[used] / counts[used, None]).astype(np.float32)
    return new_pos, new_norm, new_uv, new_tris, cell


def write_glb(path, doc, blob, pos, normal, uv, tris):
    image_payloads = []
    for img in doc.get("images", []):
        bv = doc["bufferViews"][img["bufferView"]]
        off = bv.get("byteOffset", 0)
        image_payloads.append(blob[off : off + bv["byteLength"]])

    chunks = []
    view_defs = []

    def add_chunk(payload, target=None):
        offset = sum(len(c) for c in chunks)
        padded = pad4(payload)
        chunks.append(padded)
        d = {"buffer": 0, "byteOffset": offset, "byteLength": len(payload)}
        if target:
            d["target"] = target
        view_defs.append(d)
        return len(view_defs) - 1

    pos_view = add_chunk(pos.astype(np.float32).tobytes(), 34962)
    norm_view = add_chunk(normal.astype(np.float32).tobytes(), 34962)
    uv_view = add_chunk(uv.astype(np.float32).tobytes(), 34962)
    if len(pos) <= 65535:
        idx_payload = tris.astype(np.uint16).reshape(-1).tobytes()
        idx_type = CT_U16
    else:
        idx_payload = tris.astype(np.uint32).reshape(-1).tobytes()
        idx_type = CT_U32
    idx_view = add_chunk(idx_payload, 34963)
    image_views = [add_chunk(p) for p in image_payloads]

    doc["bufferViews"] = view_defs
    doc["accessors"] = [
        {
            "bufferView": pos_view,
            "componentType": CT_FLOAT,
            "count": int(len(pos)),
            "max": [float(x) for x in pos.max(axis=0)],
            "min": [float(x) for x in pos.min(axis=0)],
            "type": "VEC3",
        },
        {"bufferView": norm_view, "componentType": CT_FLOAT, "count": int(len(normal)), "type": "VEC3"},
        {"bufferView": uv_view, "componentType": CT_FLOAT, "count": int(len(uv)), "type": "VEC2"},
        {"bufferView": idx_view, "componentType": idx_type, "count": int(tris.size), "type": "SCALAR"},
    ]
    primitive = doc["meshes"][0]["primitives"][0]
    primitive["attributes"] = {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2}
    primitive["indices"] = 3

    for img, view in zip(doc.get("images", []), image_views):
        img["bufferView"] = view
    binary = b"".join(chunks)
    doc["buffers"] = [{"byteLength": len(binary)}]
    doc["asset"]["generator"] = f"{doc['asset'].get('generator', '')} + local vertex clustering".strip()

    json_bytes = pad4(json.dumps(doc, separators=(",", ":")).encode("utf8"), b" ")
    bin_bytes = pad4(binary)
    total = 12 + 8 + len(json_bytes) + 8 + len(bin_bytes)
    out = b"glTF" + struct.pack("<II", 2, total)
    out += struct.pack("<I4s", len(json_bytes), b"JSON") + json_bytes
    out += struct.pack("<I4s", len(bin_bytes), b"BIN\x00") + bin_bytes
    path.write_bytes(out)


def simplify_glb(src: Path, dst: Path, target_tris: int):
    doc, blob = read_glb(src)
    primitive = doc["meshes"][0]["primitives"][0]
    attrs = primitive["attributes"]
    pos = accessor_array(doc, blob, attrs["POSITION"])
    normal = accessor_array(doc, blob, attrs["NORMAL"])
    uv = accessor_array(doc, blob, attrs["TEXCOORD_0"])
    indices = accessor_array(doc, blob, primitive["indices"]).astype(np.uint32)
    new_pos, new_norm, new_uv, new_tris, cell = simplify_arrays(pos, normal, uv, indices, target_tris)
    write_glb(dst, doc, blob, new_pos, new_norm, new_uv, new_tris)
    return {
        "source_tris": int(indices.size // 3),
        "target_tris": int(target_tris),
        "output_tris": int(len(new_tris)),
        "output_vertices": int(len(new_pos)),
        "cell": cell,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--target-tris", type=int, required=True)
    args = ap.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    stats = simplify_glb(args.input, args.output, args.target_tris)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
