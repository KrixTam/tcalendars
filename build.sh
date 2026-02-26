find . -type d -name "dist" -exec rm -rf {} +
find . -type d -name "tcalendars.egg-info" -exec rm -rf {} +
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
python -m build