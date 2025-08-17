# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

INFINITAS Result Notebook (inf-notebook) is a Windows desktop application for beatmania IIDX INFINITAS players that automatically captures and analyzes gameplay results using advanced image recognition.

## Key Technologies

- **Python 3.12** with WebUI2 for web-based GUI
- **Image Recognition**: Custom neural network models for OCR (stored as .npy/.res files)
- **Data Storage**: Google Cloud Storage integration for model distribution
- **Build System**: cx_Freeze for Windows executable creation

## Development Setup

1. **Environment Setup**:
   ```bash
   # Uses mise + uv for Python environment management
   # .mise.toml configures Python 3.12 with virtual environment
   
   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Running the Application**:
   ```bash
   python main.pyw
   ```

## Core Architecture

- **main.pyw**: Entry point - Windows GUI app that monitors INFINITAS window
- **recog.py**: Core image recognition engine
- **resources.py**: Resource management for trained models
- **web/**: WebUI-based interface for viewing results
- **record.py/result.py**: Data structures for gameplay records
- **storage.py**: Google Cloud Storage sync functionality

## Build & Deployment

1. **Build Executable**:
   ```bash
   python setup.py build
   ```

2. **CI/CD**: GitHub Actions workflow (`.github/workflows/main.yml`) builds releases on version tags

3. **Resource Updates**: Trained models are distributed via Google Cloud Storage

## Testing & Development

- **Manage Mode**: Debug mode accessed through UI for real-time screenshot testing
- **Annotation Tools**: `annotation_*.pyw` files for training data preparation
- **Resource Generation**: `resources_generate_*.py` scripts for model updates

## Important Notes

- This is a Windows-specific application designed for beatmania IIDX INFINITAS
- Hotkeys: Alt+F10 (screenshot), Alt+F11 (recent results), Alt+F12 (quit)
- Settings stored in `setting.json`
- No formal test suite - testing done through manage mode and manual verification