import threading
import uvicorn
import streamlit
import streamlit.web.bootstrap
import sys
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def run_fastapi():
    """Run the FastAPI backend server"""
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("core.fastapi_backend:app", host="127.0.0.1", port=port, reload=False)


def run_streamlit():
    """Run the Streamlit frontend application"""
    # Get the absolute path to your streamlit app
    streamlit_app_path = os.path.abspath("streamlit_app.py")

    # Set up command line arguments
    sys.argv = ["streamlit", "run", streamlit_app_path, "--server.port", "8501"]

    # Use the correct bootstrap method with required arguments
    streamlit.web.bootstrap.run(
        main_script_path=streamlit_app_path,
        is_hello=False,
        args=[],
        flag_options={}
    )


if __name__ == "__main__":
    # Start FastAPI in a separate thread
    fastapi_thread = threading.Thread(target=run_fastapi)
    fastapi_thread.daemon = True
    fastapi_thread.start()

    # Give FastAPI time to start up
    print("Starting FastAPI backend...")
    time.sleep(2)

    # Run Streamlit in the main thread
    print("Starting Streamlit frontend...")
    run_streamlit()