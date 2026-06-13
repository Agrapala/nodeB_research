#!/usr/bin/env python3
"""
hospital_node_client.py  —  PoCL Hospital Node Client
======================================================
Run this on each hospital laptop to:
  1. Train the local CNN on this hospital's chest X-ray data
  2. Send the trained model + metadata to the central PoCL server
 
Usage (one-time setup on each laptop):
--------------------------------------
  pip install tensorflow numpy opencv-python
 
Run:
----
  python hospital_node_client.py --node A --server_ip 100.64.0.1
  python hospital_node_client.py --node B --server_ip 100.64.0.1
  python hospital_node_client.py --node C --server_ip 100.64.0.1
  python hospital_node_client.py --node D --server_ip 100.64.0.1
 
Arguments:
----------
  --node        A / B / C / D         Which hospital node this laptop is
  --server_ip   <Tailscale IP>        IP of the central PoCL server
  --server_port 8888                  File-transfer port  (default 8888)
  --data_dir    data/Node_X           Override data folder
  --epochs      10                    Training epochs (default 10)
  --train_only                        Only train, don't send to server
  --send_only                         Only send existing output, skip training
 
Node -> Hospital mapping  (edit NODE_CONFIG below to customise):
----------------------------------------------------------------
  A  ->  Colombo General Hospital   (Laptop A)
  B  ->  Kandy Teaching Hospital    (Laptop B)
  C  ->  Galle District Hospital    (Laptop C)
  D  ->  Jaffna Teaching Hospital   (Laptop D)
"""
 
import os
import sys
import json
import socket
import hashlib
import struct
import argparse
import numpy as np
from pathlib import Path
from datetime import datetime
 
# ── Node identity — edit these to match your deployment ──────────────────────
NODE_CONFIG = {
    "A": {
        "node_id":  "nodeA",
        "name":     "Colombo General Hospital",
        "location": "Colombo, Sri Lanka",
        "address":  "0xAC35B995FE7Bb8FcdA4b3fc2D209fb1fCbdc4345",
        "data_dir": "data/Node_A",
        "out_dir":  "output",
    },
    "B": {
        "node_id":  "nodeB",
        "name":     "Kandy Teaching Hospital",
        "location": "Kandy, Sri Lanka",
        "address":  "0xBBB0000000000000000000000000000000000002",
        "data_dir": "data/Node_B",
        "out_dir":  "output",
    },
    "C": {
        "node_id":  "nodeC",
        "name":     "Galle District Hospital",
        "location": "Galle, Sri Lanka",
        "address":  "0xCCC0000000000000000000000000000000000003",
        "data_dir": "data/Node_C",
        "out_dir":  "output",
    },
    "D": {
        "node_id":  "nodeD",
        "name":     "Jaffna Teaching Hospital",
        "location": "Jaffna, Sri Lanka",
        "address":  "0xDDD0000000000000000000000000000000000004",
        "data_dir": "data/Node_D",
        "out_dir":  "output",
    },
}
 
IMG_SIZE   = 128
BATCH_SIZE = 32
CHUNK_SIZE = 8192
 
 
# =============================================================================
# STEP 1  BUILD DATASET
# =============================================================================
 
def build_dataset(data_dir: str):
    """Load images from data_dir/PNEUMONIA (and optionally NORMAL)."""
    try:
        import cv2
    except ImportError:
        print("ERROR: opencv-python not installed.  Run:  pip install opencv-python")
        sys.exit(1)
 
    pneumonia_dir = os.path.join(data_dir, "PNEUMONIA")
    normal_dir    = os.path.join(data_dir, "NORMAL")
 
    if not os.path.isdir(pneumonia_dir):
        print(f"ERROR: PNEUMONIA folder not found: {pneumonia_dir}")
        sys.exit(1)
 
    def load_images(folder, label):
        imgs, labels = [], []
        for f in Path(folder).iterdir():
            if f.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
                continue
            img = cv2.imread(str(f), cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            imgs.append(cv2.resize(img, (IMG_SIZE, IMG_SIZE)))
            labels.append(label)
        return imgs, labels
 
    p_imgs, p_labels = load_images(pneumonia_dir, 1)
    print(f"  Loaded {len(p_imgs)} PNEUMONIA images")
 
    if os.path.isdir(normal_dir) and any(Path(normal_dir).iterdir()):
        n_imgs, n_labels = load_images(normal_dir, 0)
        print(f"  Loaded {len(n_imgs)} NORMAL images")
    else:
        print(f"  No NORMAL folder found - synthesising {len(p_imgs)} synthetic normals")
        n_imgs, n_labels = [], []
        for img in p_imgs:
            blurred   = cv2.GaussianBlur(img, (15, 15), 0)
            synthetic = np.clip(blurred * 0.6 + 40, 0, 255).astype(np.uint8)
            n_imgs.append(synthetic)
            n_labels.append(0)
 
    all_imgs   = np.array(p_imgs + n_imgs, dtype=np.float32) / 255.0
    all_labels = np.array(p_labels + n_labels, dtype=np.float32)
    all_imgs   = all_imgs[..., np.newaxis]
 
    idx        = np.random.permutation(len(all_imgs))
    all_imgs   = all_imgs[idx]
    all_labels = all_labels[idx]
 
    split = int(0.8 * len(all_imgs))
    return all_imgs[:split], all_labels[:split], all_imgs[split:], all_labels[split:]
 
 
# =============================================================================
# STEP 2  BUILD CNN  (mirrors cnn_model.py on the server)
# =============================================================================
 
def build_cnn():
    try:
        import tensorflow as tf
    except ImportError:
        print("ERROR: TensorFlow not installed.  Run:  pip install tensorflow")
        sys.exit(1)
 
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(IMG_SIZE, IMG_SIZE, 1)),
        tf.keras.layers.Conv2D(32, (3,3), activation='relu', padding='same'),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.MaxPooling2D(2, 2),
        tf.keras.layers.Conv2D(64, (3,3), activation='relu', padding='same'),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.MaxPooling2D(2, 2),
        tf.keras.layers.Conv2D(128, (3,3), activation='relu', padding='same'),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.MaxPooling2D(2, 2),
        tf.keras.layers.GlobalAveragePooling2D(),
        tf.keras.layers.Dense(256, activation='relu'),
        tf.keras.layers.Dropout(0.5),
        tf.keras.layers.Dense(1, activation='sigmoid'),
    ])
    return model
 
 
# =============================================================================
# STEP 3  TRAIN
# =============================================================================
 
def train(node_key: str, cfg: dict, epochs: int) -> dict:
    """Train the local CNN and save model_best.h5 + metadata.json."""
    import tensorflow as tf
 
    data_dir = cfg["data_dir"]
    out_dir  = cfg["out_dir"]
    os.makedirs(out_dir, exist_ok=True)
 
    print(f"\n{'='*58}")
    print(f"  Hospital : {cfg['name']}")
    print(f"  Location : {cfg['location']}")
    print(f"  Data     : {data_dir}")
    print(f"{'='*58}")
 
    print("  Loading images...")
    X_train, y_train, X_val, y_val = build_dataset(data_dir)
    print(f"  Train samples: {len(X_train)}   Val samples: {len(X_val)}")
 
    model = build_cnn()
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-3),
        loss="binary_crossentropy",
        metrics=[
            "accuracy",
            tf.keras.metrics.AUC(name="auc"),
            tf.keras.metrics.Precision(name="precision"),
            tf.keras.metrics.Recall(name="recall"),
        ],
    )
 
    model_path = os.path.join(out_dir, "model_best.h5")
 
    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(
            model_path, monitor="val_accuracy",
            save_best_only=True, verbose=0),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_accuracy", patience=4,
            restore_best_weights=True, verbose=1),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=2, verbose=1),
    ]
 
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=epochs,
        batch_size=BATCH_SIZE,
        callbacks=callbacks,
        verbose=1,
    )
 
    # Re-load and evaluate the best saved checkpoint
    best = tf.keras.models.load_model(model_path, compile=False)
    best.compile(
        optimizer=tf.keras.optimizers.Adam(),
        loss="binary_crossentropy",
        metrics=["accuracy",
                 tf.keras.metrics.AUC(name="auc"),
                 tf.keras.metrics.Precision(name="precision"),
                 tf.keras.metrics.Recall(name="recall")],
    )
    raw          = best.evaluate(X_val, y_val, verbose=0)
    val_loss     = float(raw[0])
    val_acc      = float(raw[1])
    val_auc      = float(raw[2])
    val_prec     = float(raw[3])
    val_rec      = float(raw[4])
    val_f1       = 2 * val_prec * val_rec / (val_prec + val_rec + 1e-8)
 
    print(f"\n  Results for {cfg['name']}:")
    print(f"     Accuracy  : {val_acc:.4f}  ({val_acc*100:.2f}%)")
    print(f"     Loss      : {val_loss:.4f}")
    print(f"     AUC       : {val_auc:.4f}")
    print(f"     Precision : {val_prec:.4f}")
    print(f"     Recall    : {val_rec:.4f}")
    print(f"     F1        : {val_f1:.4f}")
 
    metadata = {
        "node_id":        cfg["node_id"],
        "name":           cfg["name"],
        "location":       cfg["location"],
        "address":        cfg["address"],
        "num_samples":    int(len(X_train)),
        "val_accuracy":   val_acc,
        "val_loss":       val_loss,
        "val_auc":        val_auc,
        "val_precision":  val_prec,
        "val_recall":     val_rec,
        "val_f1":         val_f1,
        "epochs_trained": int(len(history.history["loss"])),
        "trained_at":     datetime.now().isoformat(),
    }
 
    meta_path = os.path.join(out_dir, "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
 
    print(f"\n  Saved: {model_path}")
    print(f"  Saved: {meta_path}")
    return metadata
 
 
# =============================================================================
# STEP 4  SEND TO SERVER  (compatible with FileTransferServer protocol)
# =============================================================================
 
def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()
 
 
def _send_file(sock: socket.socket, filepath: str, label: str):
    """
    Send one file using the FileTransferServer wire protocol:
      [4 bytes big-endian]  filename length
      [N bytes]             filename (UTF-8)
      [8 bytes big-endian]  file size in bytes
      [M bytes]             raw file data in CHUNK_SIZE pieces
      [64 bytes]            SHA-256 hex digest
    """
    filename  = os.path.basename(filepath)
    file_size = os.path.getsize(filepath)
    file_hash = _sha256(filepath)
 
    fn_bytes = filename.encode("utf-8")
    sock.sendall(struct.pack(">I", len(fn_bytes)))
    sock.sendall(fn_bytes)
    sock.sendall(struct.pack(">Q", file_size))
 
    sent = 0
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            sock.sendall(chunk)
            sent += len(chunk)
            pct   = sent / file_size * 100
            print(f"\r  Sending {label}: {pct:5.1f}%  ({sent:,} / {file_size:,} bytes)", end="", flush=True)
    print()
 
    sock.sendall(file_hash.encode("utf-8"))
    print(f"  SHA-256 : {file_hash[:20]}...")
 
 
def send_to_server(cfg: dict, server_ip: str, server_port: int):
    """Upload model_best.h5 + metadata.json to the central PoCL server."""
    out_dir    = cfg["out_dir"]
    node_id    = cfg["node_id"]
    model_path = os.path.join(out_dir, "model_best.h5")
    meta_path  = os.path.join(out_dir, "metadata.json")
 
    if not os.path.exists(model_path):
        print(f"ERROR: model not found at {model_path}")
        print("       Train first (remove --send_only flag).")
        sys.exit(1)
    if not os.path.exists(meta_path):
        print(f"ERROR: metadata not found at {meta_path}")
        sys.exit(1)
 
    print(f"\nConnecting to PoCL server at {server_ip}:{server_port}...")
    for attempt in range(1, 4):  # 3 attempts
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            sock.settimeout(300)  # 5 minutes — large model files need time
            sock.connect((server_ip, server_port))
            print(f"  Connected! (attempt {attempt})\n")
            break
        except Exception as e:
            print(f"  Attempt {attempt}/3 failed: {e}")
            if attempt == 3:
                print(f"\nERROR: Cannot reach server after 3 attempts.")
                print(f"  1. Make sure file_transfer_server.py is running on the server")
                print(f"  2. Make sure Tailscale is connected on both machines")
                print(f"  3. Verify server IP: {server_ip}")
                sys.exit(1)
            import time; time.sleep(3)
 
    # Handshake: tell server which node this is so it saves to received_models/nodeX/
    node_bytes = node_id.encode("utf-8")
    sock.sendall(struct.pack(">I", len(node_bytes)))
    sock.sendall(node_bytes)
 
    _send_file(sock, model_path, "model_best.h5")
    _send_file(sock, meta_path,  "metadata.json")
    sock.close()
 
    print(f"\n  Transfer complete!  {node_id} -> {server_ip}:{server_port}")
    print(f"  View results at:   http://{server_ip}:5004/monitoring\n")
 
 
# =============================================================================
# ENTRY POINT
# =============================================================================
 
def main():
    parser = argparse.ArgumentParser(
        description="PoCL Hospital Node Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Train and send (normal workflow):
    python hospital_node_client.py --node A --server_ip 100.64.0.1
 
  Train only (no internet / server offline):
    python hospital_node_client.py --node B --server_ip 100.64.0.1 --train_only
 
  Re-send previously trained model:
    python hospital_node_client.py --node C --server_ip 100.64.0.1 --send_only
 
  Custom data folder and more epochs:
    python hospital_node_client.py --node D --server_ip 100.64.0.1 --data_dir /path/to/data --epochs 20
        """,
    )
    parser.add_argument(
        "--node", required=True, choices=["A", "B", "C", "D"],
        help="Which node this laptop represents (A=Colombo, B=Kandy, C=Galle, D=Jaffna)",
    )
    parser.add_argument(
        "--server_ip", default="100.64.0.1",
        help="Tailscale IP of the central PoCL server (default: 100.64.0.1)",
    )
    parser.add_argument(
        "--server_port", type=int, default=8888,
        help="File-transfer port on the server (default: 8888)",
    )
    parser.add_argument(
        "--data_dir", default=None,
        help="Override data directory (default from NODE_CONFIG)",
    )
    parser.add_argument(
        "--epochs", type=int, default=10,
        help="Training epochs (default: 10)",
    )
    parser.add_argument(
        "--train_only", action="store_true",
        help="Train only — do not send to server",
    )
    parser.add_argument(
        "--send_only", action="store_true",
        help="Send existing model only — skip training",
    )
    args = parser.parse_args()
 
    cfg = NODE_CONFIG[args.node].copy()
    if args.data_dir:
        cfg["data_dir"] = args.data_dir
 
    print("\n" + "="*58)
    print("  PoCL Hospital Node Client")
    print(f"  Node     : {args.node}  ({cfg['node_id']})")
    print(f"  Hospital : {cfg['name']}")
    print(f"  Location : {cfg['location']}")
    if not args.train_only:
        print(f"  Server   : {args.server_ip}:{args.server_port}")
    print("="*58 + "\n")
 
    if not args.send_only:
        train(args.node, cfg, args.epochs)
 
    if not args.train_only:
        send_to_server(cfg, args.server_ip, args.server_port)
 
    print("Done.")
 
 
if __name__ == "__main__":
    main()