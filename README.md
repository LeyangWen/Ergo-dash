# Ergo-dash

A dashboard application to display videos and statistics in localhost, using Dash.

## Features

- 📹 **Video Library**: Display and manage ergonomic assessment videos
- 📊 **Statistics Dashboard**: Visualize ergonomic scores, posture incidents, and activity levels
- 📈 **Interactive Charts**: Track trends over time with interactive Plotly charts
- 🎯 **Real-time Metrics**: Monitor current activity levels with gauge displays
- 📱 **Responsive Design**: Bootstrap-based responsive layout for all screen sizes

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/LeyangWen/Ergo-dash.git
cd Ergo-dash
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Running the Dashboard

Start the dashboard server:
```bash
python app.py
```

The dashboard will be available at: **http://localhost:8050**

Press `Ctrl+C` to stop the server.

### Dashboard Components

#### 1. Video Library
- Select videos from the dropdown menu
- Play videos directly in the browser
- View video descriptions

#### 2. Statistics Summary Cards
- **Average Ergonomic Score**: Overall ergonomic performance
- **Total Incidents**: Number of posture-related incidents
- **Average Activity**: Activity level percentage

#### 3. Interactive Charts
- **Ergonomic Score Trend**: Line chart showing score progression over time
- **Posture Incidents**: Bar chart displaying incident frequency
- **Activity Gauge**: Real-time activity level indicator

## Customization

### Adding Your Own Videos

The dashboard currently uses sample videos for demonstration. To add your own videos:

1. Create a `videos` directory in the project root:
```bash
mkdir videos
```

2. Place your video files in the `videos` directory

3. Update the `SAMPLE_VIDEOS` list in `app.py`:
```python
SAMPLE_VIDEOS = [
    {
        'name': 'Your Video Name',
        'url': '/path/to/your/video.mp4',  # or URL
        'description': 'Video description'
    },
    # Add more videos...
]
```

### Customizing Statistics

To use your own data instead of sample data, modify the `generate_sample_data()` function in `app.py` to load data from your source (CSV, database, API, etc.).

## Technology Stack

- **[Dash](https://dash.plotly.com/)**: Web application framework
- **[Plotly](https://plotly.com/)**: Interactive charting library
- **[Pandas](https://pandas.pydata.org/)**: Data manipulation and analysis
- **[Bootstrap](https://getbootstrap.com/)**: UI components and styling

## Project Structure

```
Ergo-dash/
├── app.py              # Main dashboard application
├── requirements.txt    # Python dependencies
├── .gitignore         # Git ignore rules
├── LICENSE            # MIT License
└── README.md          # This file
```

## Development

### Running in Debug Mode

The application runs in debug mode by default, which enables:
- Automatic reloading when code changes
- Detailed error messages
- Interactive debugger

To run in production mode, modify the last line of `app.py`:
```python
app.run(debug=False, host='0.0.0.0', port=8050)
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Author

Leyang Wen

## Acknowledgments

- Built with [Dash by Plotly](https://dash.plotly.com/)
- Sample videos provided by W3Schools for demonstration purposes