#!/usr/bin/env python3
"""
Test script to verify Ergo-dash installation and functionality.
Run this script to check if all dependencies are installed correctly.
"""

def test_imports():
    """Test that all required packages can be imported."""
    print("Testing imports...")
    try:
        import dash
        print(f"  ✓ dash ({dash.__version__})")
    except ImportError as e:
        print(f"  ✗ dash: {e}")
        return False
    
    try:
        import dash_bootstrap_components as dbc
        print(f"  ✓ dash-bootstrap-components ({dbc.__version__})")
    except ImportError as e:
        print(f"  ✗ dash-bootstrap-components: {e}")
        return False
    
    try:
        import pandas as pd
        print(f"  ✓ pandas ({pd.__version__})")
    except ImportError as e:
        print(f"  ✗ pandas: {e}")
        return False
    
    try:
        import plotly
        print(f"  ✓ plotly ({plotly.__version__})")
    except ImportError as e:
        print(f"  ✗ plotly: {e}")
        return False
    
    return True

def test_app_creation():
    """Test that the app can be created successfully."""
    print("\nTesting app creation...")
    try:
        from app import app, df, SAMPLE_VIDEOS
        print(f"  ✓ App created successfully")
        print(f"  ✓ Sample data loaded: {len(df)} records")
        print(f"  ✓ Videos configured: {len(SAMPLE_VIDEOS)} videos")
        return True
    except Exception as e:
        print(f"  ✗ App creation failed: {e}")
        return False

def test_chart_creation():
    """Test that charts can be created."""
    print("\nTesting chart creation...")
    try:
        from app import (create_ergonomic_score_chart, 
                         create_posture_incidents_chart, 
                         create_activity_gauge)
        
        create_ergonomic_score_chart()
        print("  ✓ Ergonomic score chart created")
        
        create_posture_incidents_chart()
        print("  ✓ Posture incidents chart created")
        
        create_activity_gauge()
        print("  ✓ Activity gauge created")
        
        return True
    except Exception as e:
        print(f"  ✗ Chart creation failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 50)
    print("Ergo-dash Installation Test")
    print("=" * 50)
    
    all_passed = True
    
    if not test_imports():
        all_passed = False
        print("\n⚠ Some imports failed. Run: pip install -r requirements.txt")
    
    if not test_app_creation():
        all_passed = False
    
    if not test_chart_creation():
        all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✓ All tests passed!")
        print("=" * 50)
        print("\nYou can now run the dashboard with:")
        print("  python app.py")
        print("\nThen open your browser to:")
        print("  http://localhost:8050")
        return 0
    else:
        print("✗ Some tests failed")
        print("=" * 50)
        return 1

if __name__ == "__main__":
    exit(main())
