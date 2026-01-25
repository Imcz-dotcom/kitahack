import os
import numpy as np
import tensorflow as tf
from sklearn.model_selection import train_test_split

# =========================
# CONFIG
# =========================
DATA_DIR = "data/raw"
CLASSES = ["help", "cannot", "speak"]
TEST_SIZE = 0.2
EPOCHS = 30
BATCH_SIZE = 16
# =========================

# Load data
X = []
y = []

for label, class_name in enumerate(CLASSES):
    class_dir = os.path.join(DATA_DIR, class_name)
    for file in os.listdir(class_dir):
        if file.endswith(".npy"):
            data = np.load(os.path.join(class_dir, file))

            # pad 1-hand data
            if data.shape[0] == 63:
                data = np.concatenate([data, np.zeros(63, dtype=np.float32)])

            X.append(data)
            y.append(label)

X = np.array(X, dtype=np.float32)
y = np.array(y)

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
os.makedirs("models", exist_ok=True)
model.save("models/hand_sign_model.keras")

print("\n✅ TensorFlow training complete.")
