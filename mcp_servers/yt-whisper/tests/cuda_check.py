import torch
import sys
import os

def check_cuda():
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    print(f"PyTorch version: {torch.__version__}")
    
    cuda_available = torch.cuda.is_available()
    print(f"CUDA available: {cuda_available}")
    
    if cuda_available:
        print(f"CUDA device count: {torch.cuda.device_count()}")
        print(f"Current device: {torch.cuda.current_device()}")
        print(f"Device name: {torch.cuda.get_device_name(0)}")
    else:
        print("CUDA is NOT available to PyTorch.")
        print("Possible reasons:")
        print("1. NVIDIA drivers are not installed or are too old.")
        print("2. The version of PyTorch installed does not support CUDA.")
        print("3. No NVIDIA GPU is present.")

    try:
        import whisper
        print(f"Whisper version: {whisper.__version__}")
    except ImportError:
        print("openai-whisper not installed.")

    try:
        import faster_whisper
        print("faster-whisper is installed.")
    except ImportError:
        print("faster-whisper not installed.")

if __name__ == "__main__":
    check_cuda()
