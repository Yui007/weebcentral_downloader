# WeebCentral Manga Downloader

A powerful and user-friendly manga downloader specifically designed for WeebCentral. Features both GUI and command-line interfaces for downloading manga chapters efficiently with multi-threading support.

# Extension

I also created an extension if you dont want to use the script.
https://github.com/Yui007/weebcentral_extension

## Features

- **User-Friendly Interface**: Choose between GUI or command-line interface
- **Flexible Chapter Selection**: Download single chapters, ranges, or entire series
- **Concurrent Downloads**: Multi-threaded chapter downloading for improved speed
- **PDF & CBZ Conversion**: Automatically convert downloaded chapters into PDF or CBZ files.
- **Image Deletion**: Option to delete image folders after conversion to save space.
- **Progress Tracking**: Real-time download progress with status updates
- **Checkpoint System**: Resume interrupted downloads
- **Smart Naming**: Automatic folder organization with clean naming
- **Error Handling**: Robust error recovery and logging system
- **Google Colab Support**: Run directly in Google Colab for cloud-based downloading

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Yui007/weebcentral_downloader.git
cd weebcentral_downloader
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Google Colab (Recommended)
Run the scraper directly in Google Colab:
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Yui007/weebcentral_downloader/blob/main/colab_run.ipynb)

1. Click the "Open in Colab" button above
2. Run the cells in order
3. Follow the prompts to download your manga
4. Use the provided compression tools for easier downloading

### GUI Version
Run the graphical interface:
```bash
python weebcentral_gui.py
```
- Check the "Convert to PDF" or "Convert to CBZ" boxes to enable conversion.
- Check the "Delete images after conversion" box to remove the original image folders.

### Command Line Version
Run the command-line version:
```bash
python weebcentral_scraper.py
```

Follow the prompts to:
- Enter manga URL
- Select chapters (single, range, or all)
- Choose output directory
- Set download delay
- Configure thread count
- Choose whether to convert to PDF or CBZ
- Choose whether to delete images after conversion

## Requirements

- Python 3.6+
- requests>=2.31.0
- beautifulsoup4>=4.12.0
- selenium>=4.15.0
- tqdm>=4.66.1
- PyQt6>=6.5.0
- fpdf2>=2.7.4
- Pillow>=9.3.0

## Configuration Options

- **Chapter Selection**: 
  - Single chapter: '5' or '23.5'
  - Range: '1-10' or '5.5-15.5'
  - All chapters: Press Enter
- **Output Directory**: Default is 'downloads'
- **Delay**: Time between chapter downloads (default: 1.0s)
- **Max Threads**: Concurrent chapter downloads (default: 4)
- **PDF/CBZ Conversion**: Options to convert chapters to PDF or CBZ (default: disabled)
- **Delete Images**: Option to delete image folders after conversion (default: disabled)

## Screenshots
![GUI](GUI.PNG)



## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Disclaimer

This tool is for educational purposes only. Please respect the terms of service of the websites you interact with.

## Support

For issues, questions, or suggestions, please open an issue in the GitHub repository.