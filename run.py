#!/usr/bin/env python3
"""
Google Dorking Tool - Main Application Entry Point
"""

import os
import sys
from app import create_app
from dotenv import load_dotenv

load_dotenv()

# Create Flask app
app = create_app()

if __name__ == '__main__':
    # Get configuration from environment
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    
    print(f"""
    ╔════════════════════════════════════════════════════════╗
    ║         Google Dorking Tool - Security Edition         ║
    ║                                                        ║
    ║  Starting Flask application...                        ║
    ║  Debug: {str(debug):40} ║
    ║  Server: http://{host}:{port:45} ║
    ║                                                        ║
    ║  For security testing authorized domains only!         ║
    ╚════════════════════════════════════════════════════════╝
    """)
    
    # Start Flask app
    app.run(
        host=host,
        port=port,
        debug=debug,
        use_reloader=debug,
        use_debugger=debug
    )
