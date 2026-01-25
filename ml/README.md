# Hand Sign Recognition ML

This project trains a neural network to recognize hand sign gestures for "help", "cannot", and "speak".

## Setup Instructions

### 1. Create Virtual Environment
```bash
cd ml
python -m venv venv
```

### 2. Activate Virtual Environment
Windows (PowerShell):
```powershell
.\venv\Scripts\Activate.ps1
```

Windows (CMD):
```cmd
venv\Scripts\activate.bat
```

### 3. Install Dependencies
```bash
pip install tensorflow opencv-python mediapipe numpy scikit-learn
```

## Project Structure
```
ml/
├── data/
│   └── raw/              # Raw training data (hand landmark coordinates)
├── models/               # Saved trained models (.keras files)
├── src/
│   ├── train/
│   │   ├── train_model.py       # Data loader script
│   │   └── train_tf_model.py    # Model training script
│   └── predict/
│       └── live_predict.py      # Real-time prediction using webcam
└── README.md
```

## Training the Model

### Collect Training Data
1. Organize hand landmark data in `ml/data/raw/` with folders named "help", "cannot", and "speak"
2. Each folder should contain `.npy` files with hand landmark coordinates (126 features: 2 hands × 21 landmarks × 3 coordinates)

### Train the Model
```bash
cd ml
python src/train/train_tf_model.py
```

This will:
- Load training data from `data/raw/`
- Train a neural network (128→64→3 neurons)
- Save the trained model to `models/hand_sign_model.keras`
- Display training and validation accuracy

**Latest Training Results:**
- Training Accuracy: 100.00%
- Validation Accuracy: 98.89%

## Using Live Prediction

Run the live prediction script to recognize hand signs in real-time:

```bash
cd ml
python src/predict/live_predict.py
```

**Controls:**
- Press `q` to quit
- Camera will show predicted class and confidence percentage
- Color coding:
  - Green (>80%): High confidence
  - Yellow (>60%): Medium confidence
  - Orange (<60%): Low confidence

## Model Details

**Classes:**
- `help`
- `cannot`
- `speak`

**Architecture:**
- Input Layer: 126 features (hand landmarks)
- Hidden Layer 1: 128 neurons (ReLU activation)
- Hidden Layer 2: 64 neurons (ReLU activation)
- Output Layer: 3 neurons (Softmax activation)

**Training Parameters:**
- Optimizer: Adam
- Loss: Sparse Categorical Crossentropy
- Batch Size: 32
- Epochs: 50
- Validation Split: 20%

## Dependencies

- **TensorFlow**: Deep learning framework
- **OpenCV (opencv-python)**: Camera access and image processing
- **MediaPipe**: Hand landmark detection
- **NumPy**: Numerical operations
- **scikit-learn**: Train/test split and evaluation metrics

## Troubleshooting

**Issue: ModuleNotFoundError**
- Make sure you activated the virtual environment
- Reinstall dependencies: `pip install -r requirements.txt` (if available)

**Issue: Camera not opening**
- Check if another application is using the camera
- Try changing camera index in `live_predict.py` from `0` to `1`

**Issue: Low prediction confidence**
- Ensure good lighting conditions
- Keep hands clearly visible to the camera
- Retrain the model with more diverse training data

## Notes

- The model expects exactly 126 features (both hands)
- Single-hand data is automatically padded with zeros to 126 features
- MediaPipe downloads the hand_landmarker.task model automatically on first run
