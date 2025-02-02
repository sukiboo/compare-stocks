import os

from src.dash_app import create_app

dash_app, server = create_app()

if __name__ == "__main__":
    dash_app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))
