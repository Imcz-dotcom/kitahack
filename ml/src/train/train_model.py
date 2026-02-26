import os
import json
import zipfile
import numpy as np
import tensorflow as tf
from sklearn.model_selection import train_test_split

# =========================
# CONFIG
# =========================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ML_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
DATA_DIR = os.path.join(ML_DIR, "data", "raw")
TEST_SIZE = 0.2
EPOCHS = 30
BATCH_SIZE = 16
EXPECTED_LEN = 63
# =========================

if not os.path.isdir(DATA_DIR):
    raise FileNotFoundError(f"Data directory not found: {DATA_DIR}")

CLASSES = sorted([
    name for name in os.listdir(DATA_DIR)
    if os.path.isdir(os.path.join(DATA_DIR, name))
])

if not CLASSES:
    raise ValueError("No class folders found in data/raw.")

print(f"Using classes: {CLASSES}")

# Load data
X = []
y = []

valid_classes = []

for class_name in CLASSES:
    class_dir = os.path.join(DATA_DIR, class_name)
    class_samples = []

    for file in os.listdir(class_dir):
        if file.endswith(".npy"):
            data = np.load(os.path.join(class_dir, file))

            if data.shape[0] != EXPECTED_LEN:
                continue

            class_samples.append(data)

    if len(class_samples) < 2:
        print(f"Skipping class '{class_name}' (need >= 2 valid samples, found {len(class_samples)})")
        continue

    label = len(valid_classes)
    valid_classes.append(class_name)
    X.extend(class_samples)
    y.extend([label] * len(class_samples))

CLASSES = valid_classes

if len(CLASSES) < 2:
    raise ValueError("Need at least 2 classes with >= 2 valid samples each to train.")

X = np.array(X, dtype=np.float32)
y = np.array(y)

if len(X) == 0:
    raise ValueError(f"No valid samples found. Expected each .npy to have length {EXPECTED_LEN}.")

print("X shape:", X.shape)
print("y shape:", y.shape)

# Train/validation split
X_train, X_val, y_train, y_val = train_test_split(
    X, y,
    test_size=TEST_SIZE,
    random_state=42,
    stratify=y
)

# Build model
model = tf.keras.Sequential([
    tf.keras.layers.Input(shape=(X.shape[1],)),
    tf.keras.layers.Dense(128, activation="relu"),
    tf.keras.layers.Dense(64, activation="relu"),
    tf.keras.layers.Dense(len(CLASSES), activation="softmax")
])

model.compile(
    optimizer="adam",
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"]
)

# Train
history = model.fit(
    X_train, y_train,
    validation_data=(X_val, y_val),
    epochs=EPOCHS,
    batch_size=BATCH_SIZE
)

# Evaluate model
print("\n" + "="*50)
print("FINAL EVALUATION")
print("="*50)

train_loss, train_acc = model.evaluate(X_train, y_train, verbose=0)
val_loss, val_acc = model.evaluate(X_val, y_val, verbose=0)

print(f"Training Accuracy: {train_acc*100:.2f}%")
print(f"Validation Accuracy: {val_acc*100:.2f}%")
print(f"Training Loss: {train_loss:.4f}")
print(f"Validation Loss: {val_loss:.4f}")

# Save model
models_dir = os.path.join(ML_DIR, "models")
os.makedirs(models_dir, exist_ok=True)
model_path = os.path.join(models_dir, "hand_sign_model.keras")
model.save(model_path)

with zipfile.ZipFile(model_path, mode="a", compression=zipfile.ZIP_DEFLATED) as zf:
    zf.writestr("assets/hand_sign_labels.json", json.dumps(CLASSES, ensure_ascii=False, indent=2))

print("Saved labels inside model: assets/hand_sign_labels.json")

print("\n✅ TensorFlow training complete.")
