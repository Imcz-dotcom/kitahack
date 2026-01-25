import os
import numpy as np

DATA_DIR = "data/raw"
EXPECTED_LENGTH = 126  # 2 hands × 21 landmarks × 3 values

# Classes to train on
CLASSES = ["help", "cannot", "speak"]

X = []
y = []
label_names = []

# Process each folder
for folder_name in os.listdir(DATA_DIR):
    folder_path = os.path.join(DATA_DIR, folder_name)
    if not os.path.isdir(folder_path):
        continue
    
    # Only process folders in CLASSES
    if folder_name not in CLASSES:
        continue
    
    # Use folder name as the gesture label
    gesture_label = folder_name
    
    if gesture_label not in label_names:
        label_names.append(gesture_label)
    
    for file in os.listdir(folder_path):
        if file.endswith(".npy"):
            data = np.load(os.path.join(folder_path, file))
            
            # Pad single-hand data to match two-hand format
            if len(data) < EXPECTED_LENGTH:
                data = np.pad(data, (0, EXPECTED_LENGTH - len(data)), constant_values=0.0)
            
            X.append(data)
            y.append(label_names.index(gesture_label))

X = np.array(X, dtype=np.float32)
y = np.array(y)

print("X shape:", X.shape)
print("y shape:", y.shape)
print("Number of classes:", len(label_names))
print("Labels:", label_names)
print("Samples per class:")
for i, label in enumerate(label_names):
    count = np.sum(y == i)
    print(f"  {label}: {count}")